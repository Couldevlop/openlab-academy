"""Paiement CinetPay de bout en bout (HTTP simulé) : initiation, notification vérifiée et idempotente, retour."""
import datetime
import hashlib
import hmac
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.paiements import PaiementIndisponible
from openlab_academy.domain.dossier_paiement import Statut, statut
from openlab_academy.domain.echeancier import Echeance, Mode
from openlab_academy.entrypoints import paiement, paiement_api
from openlab_academy.infrastructure.cinetpay import CHAMPS_JETON
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
from openlab_academy.tests.http_simule import Reponse
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, tarif, utilisateur
from openlab_academy.tests.test_paiement_inscription_frappe import cohorte, dossier_de, inscrire

SITE, CLE, SECRET = "105890", "cle-api-frappe-123", "secret-frappe-456"
BASE = "https://academy.openlab.ci"
API = f"{BASE}/api/method/openlab_academy.entrypoints.paiement_api"
PAIEMENT = "Paiement OpenLab"
AUJOURDHUI = datetime.date.today()


def jeton(corps, secret=SECRET):
    donnees = "".join(str(corps.get(c, "")) for c in CHAMPS_JETON)
    return hmac.new(secret.encode(), donnees.encode(), hashlib.sha256).hexdigest()


class CinetPaySimule:
    """`requests.post` simulé : initiation acceptée, contrôle au statut et au montant choisis."""

    def __init__(self, statut="ACCEPTED", montant="10000", erreur=None):
        self.statut, self.montant, self.erreur = statut, montant, erreur
        self.appels = []

    def __call__(self, url, json=None, **options):
        self.appels.append((url, json, options))
        if self.erreur:
            raise self.erreur
        if url.endswith("/check"):
            return Reponse(json={"code": "00", "data": {"amount": self.montant, "currency": "XOF",
                                                        "status": self.statut}})
        return Reponse(json={"code": "201", "data": {"payment_url": "https://checkout.cinetpay.com/p/1"}})

    def controles(self):
        return [a for a in self.appels if a[0].endswith("/check")]


class Base(FrappeTestCase):
    def setUp(self):
        self.cours = cours("Parcours CinetPay")
        frappe.db.set_value("User", utilisateur(), "last_name", "Kouassi")
        tarif(self.cours).insert(ignore_permissions=True)
        inscrire(cohorte(self.cours))
        self.dossier = dossier_de(self.cours)
        self.regler()

    def tearDown(self):
        frappe.db.rollback()

    def regler(self, **champs):
        r = frappe.get_single("Reglages Paiement OpenLab")
        r.update({"jour_echeance": 10, "delais_rappel": "7,3,1", "inscription_tardive_mois": 2,
                  "cinetpay_site_id": SITE, "cinetpay_api_key": CLE, "cinetpay_secret": SECRET,
                  "cinetpay_url_notification_base": BASE + "/", **champs})
        r.save(ignore_permissions=True)

    def initier(self, simule=None):
        with mock.patch("requests.post", side_effect=simule or CinetPaySimule()):
            return paiement.initier_paiement(ELEVE, self.cours)

    def transaction(self):
        return frappe.get_all(PAIEMENT, {"dossier": self.dossier}, pluck="reference")[0]

    def notifier(self, transaction, simule, x_token=None, falsifier=None, **autres):
        corps = {"cpm_site_id": SITE, "cpm_trans_id": transaction, "cpm_trans_date": "2026-10-22 10:00:00",
                 "cpm_amount": "10000", "cpm_currency": "XOF", "payment_method": "OM", **autres}
        jeton_envoye = jeton(corps) if x_token is None else x_token
        corps.update(falsifier or {})
        avant = frappe.local.form_dict
        frappe.local.form_dict = frappe._dict(corps, cmd="openlab_academy.entrypoints.paiement_api.notification_cinetpay")
        try:
            with mock.patch("requests.post", side_effect=simule), \
                    mock.patch.object(paiement_api.frappe, "get_request_header",
                                      side_effect=lambda nom, *_: jeton_envoye if nom.lower() == "x-token" else None), \
                    mock.patch.object(paiement_api.frappe, "log_error") as consigne,                     mock.patch.object(frappe.db, "rollback") as self.annulation:
                # en production, l'annulation ne vise que la requête : les données du test doivent lui survivre
                self.assertIsNone(paiement_api.notification_cinetpay())
        finally:
            frappe.local.form_dict = avant
        return consigne

    def paiements(self):
        return frappe.get_all(PAIEMENT, {"dossier": self.dossier}, ["montant", "statut", "moyen"])

    def journal(self):
        return frappe.get_all("Journal Paiement OpenLab", {"dossier": self.dossier, "action": "paiement_confirme"},
                              ["acteur", "avant", "apres"])

    def statut(self):
        d = DepotDossiersFrappe().charger(ELEVE, self.cours).dossier
        return statut(d, AUJOURDHUI)


class TestInitiation(Base):
    def test_corps_exact_et_paiement_en_attente(self):
        simule = CinetPaySimule()
        self.assertEqual(self.initier(simule), "https://checkout.cinetpay.com/p/1")
        (url, corps, options), = simule.appels
        transaction = self.transaction()
        self.assertRegex(transaction, rf"^OLA-{self.dossier}-\d{{20}}$")
        self.assertEqual(url, "https://api-checkout.cinetpay.com/v2/payment")
        self.assertEqual(corps, {
            "apikey": CLE, "site_id": SITE, "transaction_id": transaction, "amount": 10000, "currency": "XOF",
            "description": f"{self.cours} - Frais d inscription", "notify_url": f"{API}.notification_cinetpay",
            "return_url": f"{API}.retour_cinetpay?cours={self.cours}", "channels": "ALL", "lang": "fr",
            "customer_name": "Kouassi", "customer_surname": "Aya", "customer_email": ELEVE})
        self.assertEqual((options["timeout"], options["allow_redirects"]), (15, False))
        self.assertEqual(self.paiements(), [frappe._dict(montant=10000, statut="en_attente", moyen="cinetpay")])

    def test_passerelle_non_configuree(self):
        self.regler(cinetpay_api_key="")
        with mock.patch("requests.post") as post, self.assertRaises(PaiementIndisponible):
            paiement.initier_paiement(ELEVE, self.cours)
        post.assert_not_called()
        self.assertEqual(self.paiements(), [])

    def test_adresse_publique_invalide(self):
        for base in ("", "ftp://academy.ci", "https://jeton@academy.ci", "https://academy.ci/?x=1"):
            with self.subTest(base=base):
                self.regler(cinetpay_url_notification_base=base)
                with mock.patch("requests.post") as post, self.assertRaises(PaiementIndisponible):
                    paiement.initier_paiement(ELEVE, self.cours)
                post.assert_not_called()

    def test_cinetpay_injoignable_paiement_echoue(self):
        import requests
        with self.assertRaises(PaiementIndisponible) as attrape:
            self.initier(CinetPaySimule(erreur=requests.ConnectionError(f"refus {CLE}")))
        self.assertNotIn(CLE, str(attrape.exception))
        self.assertEqual([p.statut for p in self.paiements()], ["echoue"])


class TestNotification(Base):
    def setUp(self):
        super().setUp()
        self.initier()

    def test_notification_verifiee_confirme_et_journalise(self):
        simule = CinetPaySimule()
        self.notifier(self.transaction(), simule)
        self.assertEqual(self.paiements(), [frappe._dict(montant=10000, statut="confirme", moyen="cinetpay")])
        self.assertEqual(simule.controles()[0][1], {"apikey": CLE, "site_id": SITE,
                                                    "transaction_id": self.transaction()})
        (entree,) = self.journal()
        self.assertEqual(entree.acteur, "CinetPay")
        self.assertEqual((frappe.parse_json(entree.avant), frappe.parse_json(entree.apres)),
                         ({"statut": "en_attente", "paye": 0, "montant": 10000},
                          {"statut": "confirme", "paye": 10000, "montant": 10000}))
        self.assertEqual(self.statut(), Statut.SOLDE)
        self.assertTrue(frappe.db.get_value(PAIEMENT, {"reference": self.transaction()}, "date_paiement"))

    def test_meme_notification_deux_fois_un_seul_paiement(self):
        simule = CinetPaySimule()
        self.notifier(self.transaction(), simule)
        self.notifier(self.transaction(), simule)
        self.assertEqual([p.statut for p in self.paiements()], ["confirme"])
        self.assertEqual((len(self.journal()), len(simule.controles())), (1, 1))

    def test_jeton_faux_rien_n_est_ecrit_ni_controle(self):
        for faux in ("0" * 64, "", jeton({"cpm_site_id": SITE}, "autre-secret")):
            with self.subTest(faux=faux):
                simule = CinetPaySimule()
                consigne = self.notifier(self.transaction(), simule, x_token=faux)
                self.assertEqual(([p.statut for p in self.paiements()], simule.appels), (["en_attente"], []))
                texte = str(consigne.call_args)
                self.assertIn("rejetée", texte)
                self.assertNotIn(CLE, texte)
                self.assertNotIn(SECRET, texte)

    def test_montant_falsifie_apres_signature_rejete(self):
        simule = CinetPaySimule()
        self.notifier(self.transaction(), simule, falsifier={"cpm_amount": "1"})
        self.assertEqual(simule.appels, [])

    def test_autre_site_rejete(self):
        simule = CinetPaySimule()
        self.notifier(self.transaction(), simule, cpm_site_id="999")
        self.assertEqual(([p.statut for p in self.paiements()], simule.appels), (["en_attente"], []))

    def test_transaction_inconnue_ignoree(self):
        simule = CinetPaySimule()
        consigne = self.notifier("OLA-inconnue-1", simule)
        self.assertEqual((simule.appels, self.journal()), ([], []))
        self.assertEqual(frappe.db.count(PAIEMENT, {"reference": "OLA-inconnue-1"}), 0)
        consigne.assert_not_called()

    def test_sans_transaction_rejete(self):
        simule = CinetPaySimule()
        self.notifier("", simule)
        self.assertEqual(simule.appels, [])

    def test_statut_refuse_marque_echoue(self):
        self.notifier(self.transaction(), CinetPaySimule(statut="REFUSED", montant="0"))
        self.assertEqual([p.statut for p in self.paiements()], ["echoue"])
        self.assertEqual(self.journal(), [])

    def test_statut_non_confirme_ne_change_rien(self):
        self.notifier(self.transaction(), CinetPaySimule(statut="WAITING_CUSTOMER_PAYMENT"))
        self.assertEqual([p.statut for p in self.paiements()], ["en_attente"])

    def test_montant_verifie_et_non_demande(self):
        depot = DepotDossiersFrappe()
        depot.remplacer_echeances(self.dossier, Mode.UNE_FOIS, (
            Echeance(AUJOURDHUI - datetime.timedelta(days=40), 10000, "Frais d'inscription"),
            Echeance(AUJOURDHUI - datetime.timedelta(days=30), 177500, "Parcours")))
        depot.creer_paiement(self.dossier, 187500, "cinetpay", "OLA-partiel-1", "en_attente")
        self.notifier("OLA-partiel-1", CinetPaySimule(montant="100000"))
        self.assertEqual(frappe.db.get_value(PAIEMENT, {"reference": "OLA-partiel-1"}, ["montant", "statut"]),
                         (100000, "confirme"))
        self.assertEqual(self.statut(), Statut.EN_RETARD)

    def test_cinetpay_injoignable_rien_ecrit_et_consigne_sans_secret(self):
        import requests
        transaction = self.transaction()
        consigne = self.notifier(transaction, CinetPaySimule(erreur=requests.Timeout(f"lent {CLE}")))
        self.annulation.assert_called_once_with()
        self.assertEqual(frappe.db.get_value(PAIEMENT, {"reference": transaction}, "statut"), "en_attente")
        self.assertEqual(self.journal(), [])
        texte = str(consigne.call_args)
        self.assertIn("CinetPay injoignable (Timeout)", texte)
        self.assertNotIn(CLE, texte)

    def test_erreur_imprevue_consignee_par_son_type(self):
        with mock.patch.object(paiement, "confirmer_paiement", side_effect=RuntimeError(f"x {SECRET}")):
            consigne = self.notifier(self.transaction(), CinetPaySimule())
        self.annulation.assert_called_once_with()
        texte = str(consigne.call_args)
        self.assertIn("RuntimeError", texte)
        self.assertNotIn(SECRET, texte)

    def test_passerelle_non_configuree_rejete(self):
        self.regler(cinetpay_secret="")
        simule = CinetPaySimule()
        self.notifier(self.transaction(), simule, x_token=jeton({"cpm_site_id": SITE}, ""))
        self.assertEqual(simule.appels, [])


class TestDepotPaiements(Base):
    def test_confirmation_unique_et_echec_sans_effet_sur_un_confirme(self):
        depot = DepotDossiersFrappe()
        depot.creer_paiement(self.dossier, 10000, "cinetpay", "OLA-x-1", "en_attente")
        self.assertTrue(depot.confirmer_paiement("cinetpay", "OLA-x-1", 9000))
        self.assertFalse(depot.confirmer_paiement("cinetpay", "OLA-x-1", 9000))
        depot.marquer_echoue("cinetpay", "OLA-x-1")
        p = depot.paiement("cinetpay", "OLA-x-1")
        self.assertEqual((p.montant, p.statut), (9000, "confirme"))
        self.assertFalse(depot.confirmer_paiement("cinetpay", "OLA-absent", 9000))
        depot.marquer_echoue("cinetpay", "OLA-absent")
        self.assertIsNone(depot.paiement("cinetpay", "OLA-absent"))

    def test_client_inconnu(self):
        self.assertEqual(DepotDossiersFrappe().client("absent@example.ci").email, "")


class TestRetourEtExposition(Base):
    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.flags.commit = False
        super().tearDown()

    def retour(self, cours):
        frappe.local.response = frappe._dict()
        paiement_api.retour_cinetpay(cours)
        self.assertEqual(frappe.local.response.type, "redirect")
        return frappe.local.response.location

    def test_redirige_vers_l_ecran_de_paiement_du_parcours(self):
        self.assertEqual(self.retour(self.cours), f"/espace/paiement/{self.cours}")

    def test_aucune_redirection_ouverte(self):
        for cours in (None, "", "https://evil.example", "//evil.example", "inexistant", ["x"]):
            with self.subTest(cours=cours):
                self.assertEqual(self.retour(cours), "/espace")

    def test_points_ouverts_aux_visiteurs_et_methodes(self):
        notif, retour = paiement_api.notification_cinetpay, paiement_api.retour_cinetpay
        self.assertIn(notif, frappe.guest_methods)
        self.assertIn(retour, frappe.guest_methods)
        self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[notif], ["POST"])
        self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[retour], ["GET", "POST"])


class TestReconciliationAuRetour(TestRetourEtExposition):
    """Notification perdue : au retour de l'apprenant connecté, ses paiements en attente sont revérifiés."""

    def setUp(self):
        super().setUp()
        self.initier()
        self.reference = self.transaction()

    def revenir(self, simule, utilisateur=ELEVE, cours=None):
        frappe.set_user(utilisateur)
        with mock.patch("requests.post", side_effect=simule),                 mock.patch.object(paiement_api.frappe, "log_error") as consigne:
            cible = self.retour(cours or self.cours)
        frappe.set_user("Administrator")
        return cible, consigne

    def statut_paiement(self):
        return frappe.db.get_value(PAIEMENT, {"reference": self.reference}, ["montant", "statut"])

    def test_paiement_regle_mais_non_notifie_confirme_au_retour(self):
        simule = CinetPaySimule(montant="10000")
        cible, _ = self.revenir(simule)
        self.assertEqual(cible, f"/espace/paiement/{self.cours}")
        self.assertEqual(self.statut_paiement(), (10000, "confirme"))
        self.assertEqual([a[1]["transaction_id"] for a in simule.controles()], [self.reference])
        self.assertEqual(len(self.journal()), 1)
        self.assertTrue(frappe.local.flags.commit)  # requête GET : l'écriture doit être validée
        self.revenir(simule)  # retour répété : idempotent, plus rien en attente
        self.assertEqual((len(simule.controles()), len(self.journal())), (1, 1))

    def test_controle_impossible_redirige_sans_rien_changer(self):
        import requests
        cible, consigne = self.revenir(CinetPaySimule(erreur=requests.Timeout(f"lent {CLE}")))
        self.assertEqual(cible, f"/espace/paiement/{self.cours}")
        self.assertEqual(self.statut_paiement(), (10000, "en_attente"))
        texte = str(consigne.call_args)
        self.assertIn("CinetPay injoignable (Timeout)", texte)
        self.assertNotIn(CLE, texte)

    def test_erreur_imprevue_redirige_et_consigne_par_son_type(self):
        with mock.patch.object(paiement, "reconcilier_paiements", side_effect=RuntimeError(f"x {SECRET}")),                 mock.patch.object(frappe.db, "rollback") as annulation:
            cible, consigne = self.revenir(CinetPaySimule())
        self.assertEqual(cible, f"/espace/paiement/{self.cours}")
        annulation.assert_called_once_with()
        self.assertIn("RuntimeError", str(consigne.call_args))
        self.assertNotIn(SECRET, str(consigne.call_args))

    def test_visiteur_ne_declenche_aucun_controle(self):
        simule = CinetPaySimule()
        cible, _ = self.revenir(simule, utilisateur="Guest")
        self.assertEqual((cible, simule.appels), (f"/espace/paiement/{self.cours}", []))
        self.assertEqual(self.statut_paiement(), (10000, "en_attente"))

    def test_parcours_inconnu_ou_d_autrui_aucun_controle(self):
        autre = utilisateur("autre.reconciliation@example.ci")
        simule = CinetPaySimule()
        self.assertEqual(self.revenir(simule, cours="inexistant")[0], "/espace")
        self.assertEqual(self.revenir(simule, utilisateur=autre)[0], f"/espace/paiement/{self.cours}")
        self.assertEqual(simule.appels, [])
        self.assertEqual(self.statut_paiement(), (10000, "en_attente"))
