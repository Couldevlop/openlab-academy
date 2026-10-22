"""Tâche quotidienne des rappels sur le site : e-mail en file d'attente Frappe, SMS et WhatsApp (HTTP simulé),
registre idempotent, échecs consignés sans secret, revérification des paiements CinetPay en attente."""
import datetime
import email
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.email.doctype.email_account.email_account import EmailAccount
from frappe.utils import add_days, getdate, now_datetime, nowdate
from rq.timeouts import JobTimeoutException

from openlab_academy import hooks
from openlab_academy.entrypoints import paiement
from openlab_academy.infrastructure.canaux import CanalEmail, CanalSms, CanalWhatsApp
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe, ReglagesPaiementFrappe
from openlab_academy.infrastructure.rappels_frappe import DepotRappelsFrappe, RegistreRappelsFrappe
from openlab_academy.tests.http_simule import Reponse
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, dossier, utilisateur

RAPPEL = "Rappel Paiement OpenLab"
PAIEMENT = "Paiement OpenLab"
REGLAGES = "Reglages Paiement OpenLab"
TELEPHONE = "+2250700000000"
SECRET_SMS, JETON_WA, CLE_CP = "secret-orange-789", "EAAG-jeton-wa-321", "cle-cinetpay-123"


def aujourd_hui() -> datetime.date:
    return getdate(nowdate())


class Http:
    """`requests.post` simulé : Orange (jeton, SMS), WhatsApp, CinetPay (contrôle)."""

    def __init__(self, sms=201, whatsapp=200, cinetpay="ACCEPTED", pendant=None):
        self.sms, self.whatsapp, self.cinetpay = sms, whatsapp, cinetpay
        self.pendant = pendant or (lambda url: None)  # observe la base au moment de l'appel
        self.appels = []

    def __call__(self, url, **options):
        self.appels.append((url, options))
        self.pendant(url)
        if "oauth" in url:
            return Reponse(json={"access_token": "acces-orange-555"})
        if "smsmessaging" in url:
            return Reponse(self.sms, json={})
        if "graph.facebook.com" in url:
            return Reponse(self.whatsapp, json={})
        if isinstance(self.cinetpay, Exception):
            raise self.cinetpay
        return Reponse(json={"code": "00", "data": {"amount": "50000", "currency": "XOF", "status": self.cinetpay}})

    def vers(self, morceau):
        return [a for a in self.appels if morceau in a[0]]


def compte_courriel():
    """Compte d'envoi par défaut (site neuf) : sans lui, Frappe refuse de mettre un e-mail en file."""
    if not frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
        frappe.get_doc({"doctype": "Email Account", "email_account_name": "Rappels test",
                        "email_id": "academy@openlab.test", "enable_outgoing": 1, "default_outgoing": 1,
                        "smtp_server": "localhost", "smtp_port": 25}).db_insert()


class Base(FrappeTestCase):
    def setUp(self):
        utilisateur()
        compte_courriel()
        self.cours = cours("Parcours rappels")
        self.limite = add_days(aujourd_hui(), 7)
        self.dossier = dossier(self.cours, telephone=TELEPHONE, frais_inscription=10000, echeances=[
            {"date_limite": add_days(aujourd_hui(), -20), "montant": 10000, "libelle": "Frais d'inscription"},
            {"date_limite": self.limite, "montant": 50000, "libelle": "Mensualité 1"}]).insert(
            ignore_permissions=True).name
        frappe.get_doc({"doctype": PAIEMENT, "dossier": self.dossier, "montant": 10000, "moyen": "virement",
                        "reference": "VIR-RAPPEL-1", "statut": "confirme"}).insert(ignore_permissions=True)
        self.regler()
        self.commit = mock.patch.object(frappe.local.db, "commit").start()
        self.addCleanup(mock.patch.stopall)
        # seules les données du test comptent, même sur un banc qui en garde d'autres
        self.mes_dossiers = {self.dossier}
        noms = DepotRappelsFrappe.noms
        mock.patch.object(DepotRappelsFrappe, "noms",
                          lambda depot: tuple(n for n in noms(depot) if n in self.mes_dossiers)).start()
        attente = DepotDossiersFrappe.paiements_en_attente_depuis
        mock.patch.object(DepotDossiersFrappe, "paiements_en_attente_depuis", lambda depot, *a: tuple(
            r for r in attente(depot, *a) if r in ("OLA-R1", "OLA-R2", "OLA-VIEUX"))).start()

    def tearDown(self):
        frappe.db.rollback()

    def regler(self, **champs):
        r = frappe.get_single(REGLAGES)
        r.update({"jour_echeance": 10, "delais_rappel": "7,3,1", "inscription_tardive_mois": 2,
                  "sms_url_jeton": "", "sms_client_id": "", "sms_client_secret": "", "sms_expediteur": "",
                  "whatsapp_phone_id": "", "whatsapp_jeton": "", "whatsapp_modele": "",
                  "cinetpay_site_id": "", "cinetpay_api_key": "", "cinetpay_secret": "", **champs})
        r.save(ignore_permissions=True)

    def tous_les_canaux(self):
        self.regler(sms_client_id="client-orange", sms_client_secret=SECRET_SMS, sms_expediteur="+2250000",
                    whatsapp_phone_id="1234567890", whatsapp_jeton=JETON_WA, whatsapp_modele="rappel_paiement")

    def rappels(self, dossier=None):
        return {r.canal: (r.jours_avant, str(r.date_limite), r.statut) for r in
                frappe.get_all(RAPPEL, {"dossier": dossier or self.dossier}, ["canal", "jours_avant", "date_limite",
                                                                              "statut"])}

    def courriels(self):
        return frappe.get_all("Email Queue Recipient", {"recipient": ELEVE}, pluck="parent")

    def executer(self, http=None):
        with mock.patch("requests.post", side_effect=http or Http()):
            return paiement._executer_rappels()


class TestEnvoyerRappels(Base):
    def test_j7_par_e_mail_une_seule_fois_canaux_non_configures_ignores(self):
        avant = set(self.courriels())
        self.assertEqual(self.executer(), 1)
        self.assertEqual(self.executer(), 0)  # la tâche tourne deux fois le même jour
        nouveaux = set(self.courriels()) - avant
        self.assertEqual(len(nouveaux), 1)
        file = frappe.get_doc("Email Queue", nouveaux.pop())
        self.assertEqual(file.status, "Not Sent")
        self.assertEqual(self.rappels(), {"email": (7, str(self.limite), "envoye"),
                                          "sms": (7, str(self.limite), "ignore"),
                                          "whatsapp": (7, str(self.limite), "ignore")})
        self.assertTrue(self.commit.called)  # chaque dossier est validé à part

    def test_texte_et_lien_du_rappel(self):
        d = DepotRappelsFrappe().charger(self.dossier)
        self.assertEqual((d.titre, d.destinataire.email, d.destinataire.telephone, d.destinataire.nom),
                         ("Parcours rappels", ELEVE, TELEPHONE, frappe.db.get_value("User", ELEVE, "full_name")))
        self.assertTrue(d.lien.endswith(f"/espace/paiement/{self.cours}"), d.lien)
        self.assertTrue(d.lien.startswith("http"))
        self.assertIsNone(DepotRappelsFrappe().charger("inexistant"))

    def test_trois_canaux_et_corps_http(self):
        self.tous_les_canaux()
        http = Http()
        self.assertEqual(self.executer(http), 3)
        sms, = http.vers("smsmessaging")
        self.assertEqual(sms[1]["json"]["outboundSMSMessageRequest"]["address"], f"tel:{TELEPHONE}")
        self.assertIn(f"50 000 FCFA à régler au plus tard le {self.limite:%d/%m/%Y} pour le parcours Parcours rappels",
                      sms[1]["json"]["outboundSMSMessageRequest"]["outboundSMSTextMessage"]["message"])
        oauth, = http.vers("oauth")
        self.assertEqual(oauth[0], "https://api.orange.com/oauth/v3/token")
        self.assertIn("Basic ", oauth[1]["headers"]["Authorization"])  # secret lu déchiffré (get_password)
        wa, = http.vers("graph.facebook.com")
        self.assertEqual(wa[1]["headers"]["Authorization"], f"Bearer {JETON_WA}")
        self.assertEqual({c: s for c, (_, _, s) in self.rappels().items()},
                         {"email": "envoye", "sms": "envoye", "whatsapp": "envoye"})
        self.assertEqual(self.executer(Http()), 0)

    def test_sms_en_erreur_les_autres_partent_echec_consigne_sans_secret(self):
        self.tous_les_canaux()
        with mock.patch.object(frappe, "log_error") as consigne:
            self.assertEqual(self.executer(Http(sms=500)), 2)
        self.assertEqual({c: s for c, (_, _, s) in self.rappels().items()},
                         {"email": "envoye", "sms": "echec", "whatsapp": "envoye"})
        consigne.assert_called_once_with("Rappel de paiement non envoyé",
                                         f"sms, dossier {self.dossier} : SMS : réponse HTTP 500")
        for secret in (SECRET_SMS, JETON_WA, "acces-orange-555", "0700000000"):
            self.assertNotIn(secret, str(consigne.call_args))
        # relancé au passage suivant, une seule fois
        self.assertEqual(self.executer(Http()), 1)
        self.assertEqual(self.rappels()["sms"][2], "envoye")

    def test_dispense_sans_rappel(self):
        self.assertIn(self.dossier, DepotRappelsFrappe().noms())
        frappe.db.set_value("Dossier Paiement OpenLab", self.dossier, "dispense", 1)
        self.assertNotIn(self.dossier, DepotRappelsFrappe().noms())
        self.assertEqual(self.executer(), 0)

    def test_dossier_en_erreur_annule_et_consigne_les_autres_continuent(self):
        autre = dossier(cours("Parcours rappels 2"), apprenant=utilisateur("eleve2.rappels@example.ci"), echeances=[
            {"date_limite": self.limite, "montant": 20000, "libelle": "Mensualité 1"}]).insert(ignore_permissions=True)
        self.mes_dossiers.add(autre.name)
        vrai = DepotRappelsFrappe.charger

        def charger(depot, nom):
            if nom == self.dossier:
                frappe.get_doc({"doctype": RAPPEL, "dossier": nom, "date_limite": self.limite, "jours_avant": 99,
                                "canal": "email", "statut": "envoye"}).insert(ignore_permissions=True)
                raise RuntimeError(f"panne {SECRET_SMS}")
            return vrai(depot, nom)
        with mock.patch.object(DepotRappelsFrappe, "charger", charger), \
                mock.patch.object(frappe, "log_error") as consigne:
            self.assertEqual(self.executer(), 1)
        self.assertEqual(self.rappels(), {})  # écriture partielle annulée
        self.assertEqual(self.rappels(autre.name)["email"][2], "envoye")
        consigne.assert_called_once_with("Rappels de paiement : dossier non traité",
                                         f"dossier {self.dossier} : RuntimeError")

    def test_transaction_perdue_entierement_annulee(self):
        with mock.patch.object(frappe.db, "rollback", side_effect=[Exception("pas de point"), None]) as annule, \
                self.assertRaises(ValueError):
            paiement._transaction(lambda: (_ for _ in ()).throw(ValueError()))
        self.assertEqual(annule.call_args_list, [mock.call(save_point=paiement.POINT_RAPPEL), mock.call()])

    def test_delais_regles(self):
        self.regler(delais_rappel="5, 2")
        self.assertEqual(ReglagesPaiementFrappe().charger().delais_rappel, (5, 2))
        self.assertEqual(self.executer(), 0)
        frappe.db.set_single_value(REGLAGES, "delais_rappel", "")
        self.assertEqual(ReglagesPaiementFrappe().charger().delais_rappel, (7, 3, 1))

    def test_canaux_assembles_depuis_les_reglages(self):
        self.tous_les_canaux()
        email, sms, whatsapp = paiement.canaux()
        self.assertIsInstance(email, CanalEmail)
        self.assertIsInstance(sms, CanalSms)
        self.assertIsInstance(whatsapp, CanalWhatsApp)
        self.assertTrue(sms.disponible() and whatsapp.disponible())
        self.regler()
        self.assertEqual([c.disponible() for c in paiement.canaux()], [True, False, False])

    def test_tache_planifiee_a_8_heures_executee_dans_la_file_longue(self):
        self.assertEqual(hooks.scheduler_events["cron"]["0 8 * * *"],
                         ["openlab_academy.entrypoints.paiement.envoyer_rappels"])
        with mock.patch.object(frappe, "enqueue") as file:
            paiement.envoyer_rappels()
        file.assert_called_once_with("openlab_academy.entrypoints.paiement._executer_rappels", queue="long",
                                     timeout=3600, job_id="openlab_rappels", deduplicate=True)

    def test_reservation_validee_avant_l_appel_statut_valide_apres(self):
        self.tous_les_canaux()
        vus = []

        def pendant(url):
            if "smsmessaging" in url:
                vus.append((self.commit.call_count, self.rappels().get("sms", (0, 0, None))[2]))
        avant = self.commit.call_count
        self.executer(Http(pendant=pendant))
        (commits, statut), = vus
        self.assertEqual(statut, "echec")  # réservation déjà écrite...
        self.assertGreater(commits, avant)  # ...et validée avant l'appel HTTP
        self.assertGreater(self.commit.call_count, commits)  # statut final validé après
        self.assertEqual(self.rappels()["sms"][2], "envoye")

    def test_delai_de_la_tache_jamais_avale(self):
        self.tous_les_canaux()
        http = Http()

        def poster(url, **options):
            if "smsmessaging" in url:
                raise JobTimeoutException("délai dépassé")
            return http(url, **options)
        with mock.patch("requests.post", side_effect=poster), self.assertRaises(JobTimeoutException):
            paiement._executer_rappels()
        with mock.patch.object(paiement, "passerelle", side_effect=JobTimeoutException()), \
                self.assertRaises(JobTimeoutException):
            paiement._executer_rappels()

    def test_sans_compte_d_envoi_e_mail_ignore_sans_alerte(self):
        with mock.patch.object(EmailAccount, "find_default_outgoing", return_value=None), \
                mock.patch.object(frappe, "log_error") as consigne:
            self.assertEqual(self.executer(), 0)
        self.assertEqual(self.rappels()["email"][2], "ignore")
        consigne.assert_not_called()

    def test_titre_echappe_dans_l_e_mail(self):
        frappe.db.set_value("LMS Course", self.cours, "title", "Parcours <b>IA</b>")
        avant = set(self.courriels())
        self.executer()
        nouveau, = set(self.courriels()) - avant
        mime = email.message_from_string(frappe.db.get_value("Email Queue", nouveau, "message"))
        corps, = [p.get_payload(decode=True).decode() for p in mime.walk() if p.get_content_type() == "text/html"]
        self.assertIn("Parcours &lt;b&gt;IA&lt;/b&gt;. Payer", corps)
        self.assertNotIn("<b>IA</b>", corps)


class TestRegistre(Base):
    def test_reserver_consigner(self):
        r, limite = RegistreRappelsFrappe(), self.limite
        self.assertTrue(r.reserver(self.dossier, limite, 7, "sms"))
        self.assertEqual(r.etats(self.dossier), {(limite, 7, "sms"): "echec"})
        self.assertTrue(r.reserver(self.dossier, limite, 7, "sms"))  # un échec reste relançable
        r.consigner(self.dossier, limite, 7, "sms", "envoye")
        self.assertFalse(r.reserver(self.dossier, limite, 7, "sms"))
        r.consigner(self.dossier, limite, 7, "email", "ignore")
        self.assertTrue(r.reserver(self.dossier, limite, 7, "email"))
        self.assertEqual(r.etats(self.dossier)[(limite, 7, "email")], "echec")
        self.assertEqual(frappe.db.count(RAPPEL, {"dossier": self.dossier}), 2)

    def test_consigner_en_meme_temps_qu_une_autre_tache(self):
        r = RegistreRappelsFrappe()
        r.consigner(self.dossier, self.limite, 3, "sms", "echec")
        messages = len(frappe.local.message_log)
        vrai, appels = frappe.db.get_value, []

        def get_value(*a, **k):
            if a and a[0] == RAPPEL and not appels:
                appels.append(a)
                return None  # la ligne n'existait pas encore quand on l'a cherchée
            return vrai(*a, **k)
        with mock.patch.object(frappe.db, "get_value", get_value):
            r.consigner(self.dossier, self.limite, 3, "sms", "envoye")
        self.assertEqual(len(frappe.local.message_log), messages)
        self.assertEqual(r.etats(self.dossier), {(self.limite, 3, "sms"): "envoye"})

    def test_reservation_concurrente_refusee(self):
        r = RegistreRappelsFrappe()
        r.consigner(self.dossier, self.limite, 3, "whatsapp", "envoye")
        messages = len(frappe.local.message_log)
        vrai = frappe.db.get_value
        with mock.patch.object(frappe.db, "get_value",
                               lambda *a, **k: None if a and a[0] == RAPPEL else vrai(*a, **k)):
            self.assertFalse(r.reserver(self.dossier, self.limite, 3, "whatsapp"))
        self.assertEqual(len(frappe.local.message_log), messages)
        self.assertEqual(r.etats(self.dossier), {(self.limite, 3, "whatsapp"): "envoye"})


class TestReverification(Base):
    def setUp(self):
        super().setUp()
        self.regler(cinetpay_site_id="105890", cinetpay_api_key=CLE_CP, cinetpay_secret="s")
        for reference, jours in (("OLA-R1", 1), ("OLA-R2", 2), ("OLA-VIEUX", 8)):
            nom = frappe.get_doc({"doctype": PAIEMENT, "dossier": self.dossier, "montant": 50000, "moyen": "cinetpay",
                                  "reference": reference, "statut": "en_attente"}).insert(ignore_permissions=True).name
            frappe.db.set_value(PAIEMENT, nom, "creation", now_datetime() - datetime.timedelta(days=jours),
                                update_modified=False)

    def statuts(self):
        return dict(frappe.get_all(PAIEMENT, {"moyen": "cinetpay", "dossier": self.dossier}, ["reference", "statut"],
                                   as_list=True))

    def test_paiements_recents_confirmes_avant_les_rappels(self):
        http = Http()
        self.assertEqual(self.executer(http), 0)  # payé entre-temps : plus de rappel
        self.assertEqual(self.statuts(), {"OLA-R1": "confirme", "OLA-R2": "confirme", "OLA-VIEUX": "en_attente"})
        self.assertEqual({a[1]["json"]["transaction_id"] for a in http.vers("/check")}, {"OLA-R1", "OLA-R2"})
        self.assertEqual(DepotDossiersFrappe().paye(self.dossier), 110000)

    def test_passerelle_injoignable_arrete_le_passage_les_rappels_partent(self):
        import requests
        http = Http()

        def poster(url, **options):
            if url.endswith("/check"):
                raise requests.Timeout(CLE_CP)
            return http(url, **options)
        with mock.patch.object(frappe, "log_error") as consigne, mock.patch("requests.post", side_effect=poster) as p:
            self.assertEqual(paiement._executer_rappels(), 1)
        self.assertEqual(len([c for c in p.call_args_list if c.args[0].endswith("/check")]), 1)
        self.assertEqual(self.statuts(), {"OLA-R1": "en_attente", "OLA-R2": "en_attente", "OLA-VIEUX": "en_attente"})
        consigne.assert_called_once_with("Paiement en ligne non revérifié",
                                         "transaction 'OLA-R1' : CinetPay injoignable (Timeout) ; passage interrompu")
        self.assertNotIn(CLE_CP, str(consigne.call_args))

    def test_passerelle_non_configuree_aucun_controle(self):
        self.regler()
        http = Http()
        self.assertEqual(self.executer(http), 1)
        self.assertEqual(http.vers("/check"), [])

    def test_revérification_en_panne_n_empeche_pas_les_rappels(self):
        with mock.patch.object(paiement, "passerelle", side_effect=RuntimeError(CLE_CP)), \
                mock.patch.object(frappe, "log_error") as consigne:
            self.assertEqual(self.executer(), 1)
        consigne.assert_called_once_with("Paiements en ligne non revérifiés", "RuntimeError")


class TestReglagesSms(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def regler(self, url):
        r = frappe.get_single(REGLAGES)
        r.update({"jour_echeance": 10, "delais_rappel": "7,3,1", "inscription_tardive_mois": 2, "sms_url_jeton": url})
        r.save(ignore_permissions=True)

    def test_url_du_jeton_reservee_a_orange(self):
        for url in ("https://evil.example.com/token", "http://api.orange.com/oauth/v3/token",
                    r"https://evil.com\.orange.com/t", "https://evil.com /.orange.com/t"):
            with self.subTest(url=url), self.assertRaisesRegex(frappe.ValidationError, "orange.com"):
                self.regler(url)
        for url in ("", "https://api.orange.com/oauth/v3/token"):
            self.regler(url)
        self.assertEqual(frappe.db.get_single_value(REGLAGES, "sms_url_jeton"), "https://api.orange.com/oauth/v3/token")
