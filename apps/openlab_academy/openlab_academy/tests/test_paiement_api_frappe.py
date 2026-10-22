"""Virements et délais par l'intendant ou l'administrateur : droits, saisie, journal sous le nom de l'acteur."""
import datetime
import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from openlab_academy.domain.dossier_paiement import Statut, statut
from openlab_academy.entrypoints import paiement, paiement_api
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
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


class TestJourCourant(FrappeTestCase):
    def test_date_du_site(self):
        self.assertEqual(paiement.jour_courant(), aujourd_hui())
