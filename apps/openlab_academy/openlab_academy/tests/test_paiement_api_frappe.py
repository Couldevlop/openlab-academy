"""API du paiement : virements et délais (intendant, administrateur) ; dossier, choix du mode et paiement de
l'apprenant (le sien seulement) ; intendance, fiche, export et résumé (droits, indicateurs, filtres)."""
import datetime
import io
import json
from unittest import mock

import frappe
import openpyxl
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, getdate, now_datetime, nowdate

from openlab_academy.domain.dossier_paiement import Statut, statut
from openlab_academy.entrypoints import paiement, paiement_api
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
from openlab_academy.infrastructure.tableaux_paiement_frappe import TableauxPaiementFrappe
from openlab_academy.tests.http_simule import Reponse
from openlab_academy.tests.test_paiement_cinetpay_frappe import BASE, CLE, SECRET, SITE, CinetPaySimule
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, tarif, utilisateur
from openlab_academy.tests.test_paiement_inscription_frappe import cohorte, dossier_de, inscrire

INTENDANT = "intendant.virements@openlab.test"
PAIEMENT = "Paiement OpenLab"
JOURNAL = "Journal Paiement OpenLab"
DOSSIER = "Dossier Paiement OpenLab"


def agent(email: str, role: str) -> str:
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Agent", "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
    return email


def aujourd_hui() -> datetime.date:
    return getdate(nowdate())


class Base(FrappeTestCase):
    def setUp(self):
        utilisateur()
        self.cours = cours("Parcours virements")
        tarif(self.cours).insert(ignore_permissions=True)
        inscrire(cohorte(self.cours))
        self.dossier = dossier_de(self.cours)
        self.intendant = agent(INTENDANT, "Intendant OpenLab")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def statut(self):
        d = DepotDossiersFrappe().charger(ELEVE, self.cours)
        return statut(d.dossier, aujourd_hui())

    def virer(self, **champs):
        args = {"dossier": self.dossier, "montant": 10000, "reference": "VIR-2026-001",
                "date_paiement": nowdate(), "motif": "Virement reçu"} | champs
        return paiement_api.enregistrer_virement(**args)

    def journal(self, action):
        return frappe.get_all(JOURNAL, {"dossier": self.dossier, "action": action},
                              ["acteur", "motif", "avant", "apres"], order_by="creation")


class TestDroits(Base):
    def test_apprenant_refuse(self):
        frappe.set_user(utilisateur())
        with self.assertRaises(frappe.PermissionError):
            self.virer()
        with self.assertRaises(frappe.PermissionError):
            paiement_api.accorder_delai(self.dossier, add_days(nowdate(), 5), "Motif")
        frappe.set_user("Administrator")
        self.assertEqual(frappe.get_all(PAIEMENT, {"dossier": self.dossier}), [])
        self.assertEqual(self.journal("virement_enregistre") + self.journal("delai_accorde"), [])
        self.assertEqual(self.statut(), Statut.EN_RETARD)

    def test_visiteur_refuse(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            self.virer()

    def test_autres_roles_du_bureau_refuses(self):
        frappe.set_user(agent("moderateur.virements@openlab.test", "Moderator"))
        with self.assertRaises(frappe.PermissionError):
            self.virer()

    def test_points_reserves_aux_connectes_et_en_post(self):
        for f in (paiement_api.enregistrer_virement, paiement_api.accorder_delai):
            with self.subTest(f=f.__name__):
                self.assertNotIn(f, frappe.guest_methods)
                self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[f], ["POST"])


class TestVirement(Base):
    def test_intendant_enregistre_le_dossier_est_debloque_et_journalise_sous_son_nom(self):
        frappe.set_user(self.intendant)
        self.virer()
        frappe.set_user("Administrator")
        p = frappe.get_doc(PAIEMENT, {"dossier": self.dossier})
        self.assertEqual((p.moyen, p.statut, p.montant, p.reference, p.auteur, p.cle),
                         ("virement", "confirme", 10000, "VIR-2026-001", self.intendant, "virement|VIR-2026-001"))
        self.assertEqual(getdate(p.date_paiement), aujourd_hui())
        self.assertEqual(self.statut(), Statut.SOLDE)
        (ligne,) = self.journal("virement_enregistre")
        self.assertEqual((ligne.acteur, ligne.motif), (self.intendant, "Virement reçu"))
        self.assertEqual(json.loads(ligne.avant), {"paye": 0, "statut": "en_retard"})
        self.assertEqual(json.loads(ligne.apres)["paye"], 10000)

    def test_administrateur_journalise_sous_son_propre_nom(self):
        frappe.set_user(self.intendant)
        self.virer(reference="VIR-I")
        frappe.set_user("Administrator")
        self.virer(reference="VIR-A", montant=5000)
        self.assertEqual([j.acteur for j in self.journal("virement_enregistre")], [self.intendant, "Administrator"])
        self.assertEqual(frappe.db.get_value(PAIEMENT, {"reference": "VIR-A"}, "auteur"), "Administrator")

    def test_requete_http_montant_en_chaine_de_chiffres(self):
        self.virer(montant="10000", reference="  VIR-HTTP ")
        self.assertEqual(frappe.db.get_value(PAIEMENT, {"dossier": self.dossier}, ["montant", "reference"]),
                         (10000, "VIR-HTTP"))

    def test_reference_en_double_refusee_et_rien_de_plus_n_est_ecrit(self):
        self.virer()
        with self.assertRaisesRegex(frappe.ValidationError, "Cette référence de virement est déjà enregistrée."):
            self.virer(montant=5000)
        self.assertEqual(frappe.get_all(PAIEMENT, {"dossier": self.dossier}, pluck="montant"), [10000])
        self.assertEqual(len(self.journal("virement_enregistre")), 1)

    def test_reference_en_double_concurrente_traduite(self):
        """L'unicité en base prime si le contrôle préalable ne voit pas encore l'autre saisie."""
        self.virer()
        reel = frappe.db.exists
        with mock.patch.object(frappe.db, "exists",
                               side_effect=lambda dt, *a, **k: False if dt == PAIEMENT else reel(dt, *a, **k)):
            with self.assertRaisesRegex(frappe.ValidationError, "déjà enregistrée"):
                self.virer(montant=5000)
        self.assertEqual(frappe.get_all(PAIEMENT, {"dossier": self.dossier}, pluck="montant"), [10000])
        self.assertEqual(len(self.journal("virement_enregistre")), 1)

    def test_saisies_invalides_refusees(self):
        cas = {"montant": [0, -5, 12.5, "abc", "1e3", "-5", True, None], "reference": ["", "  ", "x" * 141],
               "date_paiement": [add_days(nowdate(), 1), "pas-une-date", ""]}
        for champ, valeurs in cas.items():
            for v in valeurs:
                with self.subTest(champ=champ, v=v), self.assertRaises(frappe.ValidationError):
                    self.virer(**{champ: v})
        self.assertEqual(frappe.get_all(PAIEMENT, {"dossier": self.dossier}), [])

    def test_dossier_inconnu_ou_dispense_refuse(self):
        with self.assertRaisesRegex(frappe.ValidationError, "Aucun dossier"):
            self.virer(dossier="inexistant")
        frappe.db.set_value(DOSSIER, self.dossier, "dispense", 1)
        with self.assertRaisesRegex(frappe.ValidationError, "dispensé"):
            self.virer()
        self.assertEqual(frappe.get_all(PAIEMENT, {"dossier": self.dossier}), [])


class TestDelai(Base):
    def test_delai_debloque_journalise_avant_apres_sous_le_nom_de_l_acteur(self):
        jusqu_au = add_days(nowdate(), 10)
        frappe.set_user(self.intendant)
        paiement_api.accorder_delai(self.dossier, jusqu_au, "Salaire versé le 5")
        frappe.set_user("Administrator")
        self.assertEqual(getdate(frappe.db.get_value(DOSSIER, self.dossier, "delai_jusqu_au")), getdate(jusqu_au))
        self.assertEqual(self.statut(), Statut.A_JOUR)
        (ligne,) = self.journal("delai_accorde")
        self.assertEqual((ligne.acteur, ligne.motif), (self.intendant, "Salaire versé le 5"))
        self.assertEqual(json.loads(ligne.avant), {"delai_jusqu_au": None, "statut": "en_retard"})
        self.assertEqual(json.loads(ligne.apres), {"delai_jusqu_au": str(getdate(jusqu_au)), "statut": "a_jour"})

    def test_administrateur_journalise_sous_son_nom(self):
        paiement_api.accorder_delai(self.dossier, add_days(nowdate(), 3), "Geste commercial")
        self.assertEqual([j.acteur for j in self.journal("delai_accorde")], ["Administrator"])

    def test_delai_passe_ou_sans_motif_refuse(self):
        for jusqu_au, motif in ((nowdate(), "M"), (add_days(nowdate(), -1), "M"), ("n'importe quoi", "M"),
                                (add_days(nowdate(), 5), ""), (add_days(nowdate(), 5), "   ")):
            with self.subTest(jusqu_au=jusqu_au, motif=motif), self.assertRaises(frappe.ValidationError):
                paiement_api.accorder_delai(self.dossier, jusqu_au, motif)
        self.assertIsNone(frappe.db.get_value(DOSSIER, self.dossier, "delai_jusqu_au"))
        self.assertEqual(self.journal("delai_accorde"), [])

    def test_dossier_dispense_refuse(self):
        frappe.db.set_value(DOSSIER, self.dossier, "dispense", 1)
        with self.assertRaisesRegex(frappe.ValidationError, "dispensé"):
            paiement_api.accorder_delai(self.dossier, add_days(nowdate(), 5), "M")


AUTRE = "autre.paiement@example.ci"
TROISIEME = "troisieme.paiement@example.ci"
INTRUS = "intrus.paiement@example.ci"
TELEPHONE = "+2250700000001"
API_LECTURE = ("mon_dossier", "intendance", "fiche", "export_intendance", "resume")
API_ECRITURE = ("choisir_mode", "payer")


def regler(**champs):
    r = frappe.get_single("Reglages Paiement OpenLab")
    r.update({"jour_echeance": 10, "delais_rappel": "7,3,1", "inscription_tardive_mois": 2,
              "cinetpay_site_id": SITE, "cinetpay_api_key": CLE, "cinetpay_secret": SECRET,
              "cinetpay_url_notification_base": BASE + "/", **champs})
    r.save(ignore_permissions=True)


def appeler(nom, utilisateur, **args):
    """Appel comme le ferait la requête HTTP : Frappe ne transmet que les paramètres de la signature."""
    frappe.set_user(utilisateur)
    try:
        return frappe.call(getattr(paiement_api, nom), **args)
    finally:
        frappe.set_user("Administrator")


class BaseLecture(FrappeTestCase):
    """Trois apprenants dans une même cohorte ; jeu à jour, en retard, soldé (dates relatives au jour du site)."""

    def setUp(self):
        regler()
        self.cours = cours("Parcours lecture paiement")
        tarif(self.cours).insert(ignore_permissions=True)
        self.cohorte = cohorte(self.cours)
        self.dossiers = {}
        for email in (utilisateur(), utilisateur(AUTRE), utilisateur(TROISIEME)):
            inscrire(self.cohorte, email)
            self.dossiers[email] = dossier_de(self.cours, email)
        utilisateur(INTRUS)
        self.intendant = agent(INTENDANT, "Intendant OpenLab")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def jeu_de_trois(self):
        """À jour (ELEVE, 55 000), en retard (AUTRE, 0), soldé (TROISIEME, 100 000), virements du jour."""
        j = aujourd_hui()
        for email, mode in ((ELEVE, "deux_tranches"), (AUTRE, "mensuel"), (TROISIEME, "une_fois")):
            d = frappe.get_doc(DOSSIER, self.dossiers[email])
            d.mode = mode
            d.set("echeances", [{"date_limite": add_days(j, -30), "montant": 10000, "libelle": "Frais d'inscription"},
                                {"date_limite": add_days(j, -5), "montant": 45000, "libelle": "Échéance"},
                                {"date_limite": add_days(j, 10), "montant": 45000, "libelle": "Échéance"}])
            d.save(ignore_permissions=True)
        self.virement(ELEVE, 55000, "VIR-LECT-A")
        self.virement(TROISIEME, 100000, "VIR-LECT-C")

    def virement(self, email, montant, reference):
        paiement.enregistrer_virement(self.intendant, self.dossiers[email], montant, reference, aujourd_hui(),
                                      "Virement reçu")


class TestDroitsLecture(BaseLecture):
    def test_methodes_http_et_jamais_ouvertes_aux_visiteurs(self):
        for nom, methodes in [(n, ["GET"]) for n in API_LECTURE] + [(n, ["POST"]) for n in API_ECRITURE]:
            with self.subTest(nom=nom):
                f = getattr(paiement_api, nom)
                self.assertNotIn(f, frappe.guest_methods)
                self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[f], methodes)

    def test_visiteur_refuse_partout(self):
        args = {"mon_dossier": {"cours": self.cours},
                "choisir_mode": {"cours": self.cours, "mode": "mensuel", "telephone": TELEPHONE},
                "payer": {"cours": self.cours}, "intendance": {}, "fiche": {"dossier": self.dossiers[ELEVE]},
                "export_intendance": {}, "resume": {}}
        for nom, a in args.items():
            with self.subTest(nom=nom), mock.patch("requests.post") as post:
                with self.assertRaises(frappe.PermissionError):
                    appeler(nom, "Guest", **a)
                post.assert_not_called()
        self.assertEqual(frappe.db.get_value(DOSSIER, self.dossiers[ELEVE], "mode"), "une_fois")

    def test_apprenant_et_correcteurs_refuses_aux_vues_agents(self):
        utilisateurs = (ELEVE, agent("correcteur.lecture@openlab.test", "Batch Evaluator"),
                        agent("moderateur.lecture@openlab.test", "Moderator"))
        args = {"intendance": {}, "fiche": {"dossier": self.dossiers[AUTRE]}, "export_intendance": {}, "resume": {}}
        for u in utilisateurs:
            for nom, a in args.items():
                with self.subTest(u=u, nom=nom), self.assertRaises(frappe.PermissionError):
                    appeler(nom, u, **a)

    def test_intendant_et_administrateur_admis(self):
        for u in (self.intendant, "Administrator"):
            for nom, a in {"intendance": {}, "fiche": {"dossier": self.dossiers[AUTRE]}, "resume": {}}.items():
                with self.subTest(u=u, nom=nom):
                    self.assertIsInstance(appeler(nom, u, **a), dict)


class TestMonDossier(BaseLecture):
    def test_son_propre_dossier(self):
        v = appeler("mon_dossier", ELEVE, cours=self.cours)
        self.assertEqual((v["cours"], v["titre"], v["mode"], v["statut"], v["paye"], v["reste"]),
                         (self.cours, "Parcours lecture paiement", "une_fois", "en_retard", 0, 10000))
        self.assertEqual(v["tarif"], {"frais_inscription": 10000, "une_fois": 100000, "deux_tranches": 110000,
                                      "mensuel": 120000})
        self.assertEqual(v["echeances"], [{"date_limite": str(aujourd_hui()), "montant": 10000,
                                           "libelle": "Frais d'inscription", "couverte": False}])
        self.assertEqual(v["prochaine"], {"date_limite": str(aujourd_hui()), "montant": 10000})
        self.assertTrue(v["paiement_en_ligne"])

    def test_aucun_secret_ni_coordonnee_d_un_autre(self):
        frappe.db.set_value(DOSSIER, self.dossiers[AUTRE], "telephone", "+2250799999999")
        texte = json.dumps(appeler("mon_dossier", ELEVE, cours=self.cours), default=str)
        for interdit in (CLE, SECRET, SITE, "+2250799999999", AUTRE, TROISIEME):
            self.assertNotIn(interdit, texte)

    def test_paiement_en_ligne_non_configure(self):
        regler(cinetpay_api_key="")
        self.assertFalse(appeler("mon_dossier", ELEVE, cours=self.cours)["paiement_en_ligne"])
        regler(cinetpay_url_notification_base="")
        self.assertFalse(appeler("mon_dossier", ELEVE, cours=self.cours)["paiement_en_ligne"])

    def test_un_autre_apprenant_ne_lit_jamais_ce_dossier(self):
        """Un utilisateur ou un dossier passé en paramètre est ignoré : seul compte l'utilisateur de la session."""
        frappe.db.set_value(DOSSIER, self.dossiers[ELEVE], "telephone", TELEPHONE)
        v = appeler("mon_dossier", AUTRE, cours=self.cours, apprenant=ELEVE, dossier=self.dossiers[ELEVE])
        self.assertEqual(v["telephone"], "")
        with self.assertRaises(frappe.DoesNotExistError):
            appeler("mon_dossier", INTRUS, cours=self.cours, apprenant=ELEVE)

    def test_parcours_invalide_ou_sans_dossier(self):
        for c in ("", "x" * 141, None):
            with self.subTest(c=c), self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
                appeler("mon_dossier", ELEVE, cours=c)
        with self.assertRaises(frappe.DoesNotExistError):
            appeler("mon_dossier", ELEVE, cours="parcours-inexistant")


class TestChoisirMode(BaseLecture):
    def test_mode_choisi_au_jour_d_echeance_regle_et_journalise(self):
        regler(jour_echeance=5)
        v = appeler("choisir_mode", ELEVE, cours=self.cours, mode="mensuel", telephone="+225 07 00 00 00 01")
        self.assertEqual((v["mode"], v["telephone"]), ("mensuel", TELEPHONE))
        self.assertGreater(len(v["echeances"]), 2)
        self.assertTrue(all(getdate(e["date_limite"]).day == 5 for e in v["echeances"][1:]))
        (j,) = frappe.get_all(JOURNAL, {"dossier": self.dossiers[ELEVE], "action": "mode"}, ["acteur"])
        self.assertEqual(j.acteur, ELEVE)

    def test_n_agit_que_sur_son_propre_dossier(self):
        appeler("choisir_mode", AUTRE, cours=self.cours, mode="mensuel", telephone=TELEPHONE,
                apprenant=ELEVE, dossier=self.dossiers[ELEVE])
        apres = frappe.get_doc(DOSSIER, self.dossiers[ELEVE])
        self.assertEqual((apres.mode, apres.telephone, len(apres.echeances)), ("une_fois", None, 1))
        self.assertEqual(frappe.db.get_value(DOSSIER, self.dossiers[AUTRE], ["mode", "telephone"]),
                         ("mensuel", TELEPHONE))
        with self.assertRaises(frappe.DoesNotExistError):
            appeler("choisir_mode", INTRUS, cours=self.cours, mode="mensuel", telephone=TELEPHONE)

    def test_saisies_refusees(self):
        for mode, tel in (("gratuit", TELEPHONE), ("mensuel", "0700"), ("mensuel", None), (None, TELEPHONE)):
            with self.subTest(mode=mode, tel=tel),                     self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
                appeler("choisir_mode", ELEVE, cours=self.cours, mode=mode, telephone=tel)
        self.assertEqual(frappe.db.get_value(DOSSIER, self.dossiers[ELEVE], "mode"), "une_fois")


class UrlDouteuse(CinetPaySimule):
    def __call__(self, url, json=None, **options):
        return Reponse(json={"code": "201", "data": {"payment_url": "http://pirate.example/p"}})


class TestPayer(BaseLecture):
    def payer(self, utilisateur=ELEVE, simule=None, **autres):
        simule = simule or CinetPaySimule()
        with mock.patch("requests.post", side_effect=simule):
            return appeler("payer", utilisateur, cours=self.cours, **autres), simule

    def paiements(self, email=ELEVE):
        return frappe.get_all(PAIEMENT, {"dossier": self.dossiers[email]}, ["name", "statut", "montant"])

    def test_url_rendue_par_cinetpay_jamais_celle_du_client(self):
        r, simule = self.payer(url="https://pirate.example/x", return_url="https://pirate.example/r")
        self.assertEqual(r, {"url": "https://checkout.cinetpay.com/p/1"})
        self.assertNotIn("pirate", json.dumps(simule.appels[0][1]))
        self.assertEqual([(p.statut, p.montant) for p in self.paiements()], [("en_attente", 10000)])

    def test_second_clic_dans_les_30_minutes_meme_transaction(self):
        premier, _ = self.payer()
        second, simule = self.payer()
        self.assertEqual(second, premier)
        self.assertEqual(simule.appels, [])
        self.assertEqual(len(self.paiements()), 1)

    def test_au_dela_de_30_minutes_nouvelle_transaction(self):
        self.payer()
        (p,) = self.paiements()
        frappe.db.set_value(PAIEMENT, p.name, "creation", add_to_date(now_datetime(), minutes=-31),
                            update_modified=False)
        _, simule = self.payer()
        self.assertEqual(len(simule.appels), 1)
        self.assertEqual(len(self.paiements()), 2)

    def test_un_autre_apprenant_ne_paie_jamais_ce_dossier(self):
        r, simule = self.payer(AUTRE, apprenant=ELEVE, dossier=self.dossiers[ELEVE])
        self.assertEqual(r["url"], "https://checkout.cinetpay.com/p/1")
        self.assertEqual(self.paiements(), [])
        self.assertEqual(len(self.paiements(AUTRE)), 1)
        self.assertEqual(simule.appels[0][1]["customer_email"], AUTRE)
        with self.assertRaises(frappe.DoesNotExistError):
            self.payer(INTRUS)

    def test_indisponible_ou_reponse_douteuse_message_sobre(self):
        for regle, simule in (({"cinetpay_api_key": ""}, None), ({}, UrlDouteuse())):
            regler(**regle)
            with self.subTest(regle=regle), mock.patch.object(paiement_api.frappe, "log_error") as consigne:
                with self.assertRaisesRegex(frappe.ValidationError, "^Le paiement en ligne n'est pas disponible"):
                    self.payer(simule=simule)
                consigne.assert_called_once()
                self.assertTrue(consigne.call_args.kwargs["defer_insert"])  # survit à l'annulation de la requête
                self.assertNotIn(CLE, str(consigne.call_args))

    def test_rien_a_payer(self):
        frappe.db.set_value(DOSSIER, self.dossiers[ELEVE], "dispense", 1)
        with self.assertRaisesRegex(frappe.ValidationError, "Aucun montant"):
            self.payer()


class TestIntendance(BaseLecture):
    def vue(self, **filtres):
        return appeler("intendance", self.intendant, **({"parcours": self.cours} | filtres))

    def test_indicateurs_exacts_sur_trois_dossiers(self):
        self.jeu_de_trois()
        v = self.vue()
        self.assertEqual(v["indicateurs"], {"encaisse_mois": 155000, "encours_30j": 90000,
                                            "en_retard": {"montant": 55000, "apprenants": 1}, "bloques": 1})
        lignes = {x["apprenant"]: x for x in v["lignes"]}
        self.assertEqual({k: (x["statut"], x["bloque"], x["paye"], x["total"]) for k, x in lignes.items()},
                         {ELEVE: ("a_jour", False, 55000, 100000), AUTRE: ("en_retard", True, 0, 100000),
                          TROISIEME: ("solde", False, 100000, 100000)})
        self.assertEqual(lignes[ELEVE]["prochaine"], {"date_limite": str(add_days(aujourd_hui(), 10)),
                                                      "montant": 45000})
        self.assertEqual((lignes[AUTRE]["nom"], lignes[AUTRE]["email"], lignes[AUTRE]["dossier"]),
                         ("Aya", AUTRE, self.dossiers[AUTRE]))
        self.assertNotIn("telephone", json.dumps(v))

    def test_statut_filtre_d_accord_avec_le_domaine(self):
        self.jeu_de_trois()
        frappe.db.set_value(DOSSIER, self.dossiers[TROISIEME], "dispense", 1)
        depot = DepotDossiersFrappe()
        for s in Statut:
            with self.subTest(statut=s):
                lignes = self.vue(statut=s.value)["lignes"]
                attendus = {e for e, n in self.dossiers.items()
                            if statut(depot.par_nom(n).dossier, aujourd_hui()) is s}
                self.assertEqual({x["apprenant"] for x in lignes}, attendus)
                self.assertTrue(all(x["statut"] == s.value for x in lignes))

    def test_filtres(self):
        self.jeu_de_trois()
        self.assertEqual([x["apprenant"] for x in self.vue(mode="mensuel")["lignes"]], [AUTRE])
        self.assertEqual(len(self.vue(cohorte=self.cohorte)["lignes"]), 3)
        self.assertEqual(self.vue(cohorte="autre-cohorte")["lignes"], [])
        j = aujourd_hui()
        self.assertEqual(len(self.vue(du=str(j), au=str(j))["lignes"]), 3)
        self.assertEqual(self.vue(du=str(add_days(j, 1)))["lignes"], [])
        self.assertEqual(self.vue(au=str(add_days(j, -1)))["lignes"], [])
        self.assertEqual(self.vue(statut="a_jour")["indicateurs"]["encaisse_mois"], 55000)

    def test_filtres_invalides_refuses(self):
        for f in ({"mode": "gratuit"}, {"statut": "bloque"}, {"du": "22/10/2026"}, {"au": "2026-02-30"},
                  {"du": "2026-10-02", "au": "2026-10-01"}, {"mode": "mensuel' OR 1=1 -- "}):
            with self.subTest(f=f), self.assertRaises(frappe.ValidationError):
                self.vue(**f)

    def test_valeur_de_filtre_jamais_interpretee_en_sql(self):
        self.jeu_de_trois()
        self.assertEqual(self.vue(parcours=f"{self.cours}' OR '1'='1")["lignes"], [])


class TestFiche(BaseLecture):
    def test_fiche_complete_avec_telephone_paiements_rappels_et_journal(self):
        self.jeu_de_trois()
        frappe.db.set_value(DOSSIER, self.dossiers[ELEVE], "telephone", TELEPHONE)
        frappe.get_doc({"doctype": "Rappel Paiement OpenLab", "dossier": self.dossiers[ELEVE],
                        "date_limite": add_days(aujourd_hui(), 10), "jours_avant": 7, "canal": "sms",
                        "statut": "envoye"}).insert(ignore_permissions=True)
        paiement.accorder_delai(self.intendant, self.dossiers[ELEVE], add_days(aujourd_hui(), 3), "Geste")
        v = appeler("fiche", self.intendant, dossier=self.dossiers[ELEVE])
        self.assertEqual((v["apprenant"], v["email"], v["telephone"], v["statut"], v["paye"], v["arriere"]),
                         (ELEVE, ELEVE, TELEPHONE, "a_jour", 55000, 0))
        self.assertEqual(v["delai_jusqu_au"], str(add_days(aujourd_hui(), 3)))
        self.assertEqual([(p["moyen"], p["reference"], p["montant"], p["auteur"]) for p in v["paiements"]],
                         [("virement", "VIR-LECT-A", 55000, self.intendant)])
        self.assertEqual([(r["canal"], r["jours_avant"], r["statut"]) for r in v["rappels"]], [("sms", 7, "envoye")])
        self.assertEqual([(j["acteur"], j["action"]) for j in v["journal"]],
                         [(self.intendant, "delai_accorde"), (self.intendant, "virement_enregistre")])
        self.assertEqual(v["journal"][0]["motif"], "Geste")
        self.assertEqual(v["journal"][1]["apres"]["paye"], 55000)
        self.assertNotIn(CLE, json.dumps(v, default=str))

    def test_dossier_inconnu(self):
        with self.assertRaisesRegex(frappe.ValidationError, "Aucun dossier"):
            appeler("fiche", self.intendant, dossier="inexistant")


class TestExport(BaseLecture):
    def test_classeur_lisible_et_formules_neutralisees(self):
        self.jeu_de_trois()
        frappe.db.set_value("User", AUTRE, "full_name", "=1+1")
        frappe.local.response = frappe._dict()
        self.assertIsNone(appeler("export_intendance", self.intendant, parcours=self.cours))
        r = frappe.local.response
        self.assertEqual(r["type"], "binary")
        self.assertEqual(r["filename"], f"intendance-paiements-{aujourd_hui()}.xlsx")
        feuille = openpyxl.load_workbook(io.BytesIO(r["filecontent"])).active
        rangees = list(feuille.iter_rows(values_only=True))
        self.assertEqual(rangees[0][:4], ("Dossier", "Apprenant", "Nom", "E-mail"))
        self.assertEqual(len(rangees), 4)
        autre = next(x for x in rangees if x[1] == AUTRE)
        self.assertEqual((autre[2], autre[12], autre[13]), ("'=1+1", "En retard", "oui"))
        self.assertTrue(all(c.data_type != "f" for ligne in feuille.iter_rows() for c in ligne))

    def test_filtre_invalide_refuse(self):
        with self.assertRaises(frappe.ValidationError):
            appeler("export_intendance", self.intendant, statut="tous")


class TestResume(BaseLecture):
    def test_resume_par_parcours_et_dernieres_actions(self):
        self.jeu_de_trois()
        for u in (self.intendant, "Administrator"):
            with self.subTest(u=u):
                v = appeler("resume", u)
                self.assertEqual(set(v), {"encaisse_mois", "evolution_pct", "taux_recouvrement", "retards",
                                          "bloques", "par_parcours", "modes", "dernieres_actions"})
                (ligne,) = [p for p in v["par_parcours"] if p["parcours"] == self.cours]
                self.assertEqual(ligne, {"parcours": self.cours, "titre": "Parcours lecture paiement", "inscrits": 3,
                                         "encaisse": 155000, "reste": 145000})
                self.assertGreaterEqual(v["encaisse_mois"], 155000)
                self.assertGreaterEqual(v["bloques"], 1)
                self.assertTrue(all(v["modes"][m] >= 1 for m in ("une_fois", "deux_tranches", "mensuel")))
                self.assertLessEqual(len(v["dernieres_actions"]), 5)
                self.assertEqual((v["dernieres_actions"][0]["acteur"], v["dernieres_actions"][0]["action"]),
                                 (self.intendant, "virement_enregistre"))


class TestAdaptateurTableaux(BaseLecture):
    def test_aucun_dossier_rien_d_encaisse_et_journal_illisible_rendu_tel_quel(self):
        t = TableauxPaiementFrappe()
        self.assertEqual(t.encaisse(aujourd_hui(), aujourd_hui(), ()), 0)
        frappe.get_doc({"doctype": JOURNAL, "dossier": self.dossiers[ELEVE], "acteur": "x", "action": "test",
                        "horodatage": now_datetime(), "avant": "pas du json", "apres": ""}
                       ).insert(ignore_permissions=True)
        (ligne,) = t.journal(self.dossiers[ELEVE], 5)
        self.assertEqual((ligne["avant"], ligne["apres"]), ("pas du json", {}))


class TestJourCourant(FrappeTestCase):
    def test_date_du_site(self):
        self.assertEqual(paiement.jour_courant(), aujourd_hui())
