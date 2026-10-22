"""Données du paiement : tarifs, réglages, dossiers, paiements, journal, rappels, rôle Intendant, patch de dispense."""
import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import install
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.patches import dispenser_inscriptions_existantes
from openlab_academy.tests.fabriques import parcours

ELEVE = "eleve.paiement@example.ci"


def utilisateur(email=ELEVE):
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Aya", "send_welcome_email": 0,
                        "roles": [{"role": "LMS Student"}]}).insert(ignore_permissions=True)
    return email


def cours(titre="Parcours paiement test"):
    return DepotFrappe(commit=False, reglages=Reglages()).creer(parcours(title=titre))


def tarif(c, **autres):
    champs = {"doctype": "Tarif Parcours OpenLab", "cours": c, "frais_inscription": 10000, "prix_une_fois": 100000,
              "prix_deux_tranches": 110000, "prix_mensuel": 120000}
    champs.update(autres)
    return frappe.get_doc(champs)


def dossier(c, **autres):
    champs = {"doctype": "Dossier Paiement OpenLab", "apprenant": utilisateur(), "cours": c}
    champs.update(autres)
    return frappe.get_doc(champs)


class TestTarif(FrappeTestCase):
    def setUp(self):
        self.cours = cours()

    def tearDown(self):
        frappe.db.rollback()

    def test_tarif_valide_enregistre(self):
        self.assertEqual(tarif(self.cours).insert(ignore_permissions=True).cours, self.cours)

    def test_non_multiple_de_5_refuse(self):
        with self.assertRaisesRegex(frappe.ValidationError, "multiples de 5"):
            tarif(self.cours, prix_une_fois=100003).insert(ignore_permissions=True)

    def test_prix_non_croissants_refuses(self):
        with self.assertRaisesRegex(frappe.ValidationError, "croître"):
            tarif(self.cours, prix_mensuel=100000).insert(ignore_permissions=True)

    def test_un_seul_tarif_par_cours(self):
        tarif(self.cours).insert(ignore_permissions=True)
        with self.assertRaises(frappe.DuplicateEntryError):
            tarif(self.cours).insert(ignore_permissions=True)


class TestReglagesPaiement(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def regler(self, **champs):
        r = frappe.get_single("Reglages Paiement OpenLab")
        r.update({"jour_echeance": 10, "delais_rappel": "7,3,1", "inscription_tardive_mois": 2, **champs})
        r.save(ignore_permissions=True)
        return r

    def test_defauts_valides(self):
        r = self.regler()
        self.assertEqual((r.jour_echeance, r.delais_rappel, r.inscription_tardive_mois), (10, "7,3,1", 2))

    def test_jour_hors_bornes_refuse(self):
        for jour in (0, 29):
            with self.assertRaisesRegex(frappe.ValidationError, "entre 1 et 28"):
                self.regler(jour_echeance=jour)

    def test_delais_invalides_refuses(self):
        for delais in ("", "7,x", "7,0", "7,7", "-3"):
            with self.assertRaisesRegex(frappe.ValidationError, "délais de rappel"):
                self.regler(delais_rappel=delais)

    def test_delais_espaces_acceptes(self):
        self.assertEqual(self.regler(delais_rappel="14, 7 ,1").delais_rappel, "14, 7 ,1")

    def test_inscription_tardive_negative_refusee(self):
        with self.assertRaisesRegex(frappe.ValidationError, "inscription tardive"):
            self.regler(inscription_tardive_mois=-1)

    def test_secrets_en_champs_password(self):
        champs = {f.fieldname: f.fieldtype for f in frappe.get_meta("Reglages Paiement OpenLab").fields}
        for nom in ("cinetpay_api_key", "cinetpay_secret", "sms_client_secret", "whatsapp_jeton"):
            self.assertEqual(champs[nom], "Password")


class TestDossier(FrappeTestCase):
    def setUp(self):
        self.cours = cours()

    def tearDown(self):
        frappe.db.rollback()

    def test_echeances_et_prix_figes(self):
        d = dossier(self.cours, mode="mensuel", frais_inscription=10000, prix_mensuel=120000)
        d.append("echeances", {"date_limite": datetime.date(2026, 11, 10), "montant": 10000, "libelle": "Inscription"})
        d.insert(ignore_permissions=True)
        self.assertEqual(frappe.get_doc("Dossier Paiement OpenLab", d.name).echeances[0].montant, 10000)

    def test_unicite_apprenant_cours(self):
        dossier(self.cours).insert(ignore_permissions=True)
        with self.assertRaises(frappe.UniqueValidationError):
            dossier(self.cours).insert(ignore_permissions=True)

    def test_un_autre_cours_est_permis(self):
        dossier(self.cours).insert(ignore_permissions=True)
        dossier(cours("Autre parcours paiement")).insert(ignore_permissions=True)

    def test_pas_d_acces_pour_un_apprenant(self):
        utilisateur()
        frappe.set_user(ELEVE)
        try:
            self.assertFalse(frappe.has_permission("Dossier Paiement OpenLab", "read"))
            self.assertFalse(frappe.has_permission("Dossier Paiement OpenLab", "write"))
        finally:
            frappe.set_user("Administrator")

    def test_lecture_seule_pour_l_intendant(self):
        permissions = {p.role: p for p in frappe.get_meta("Dossier Paiement OpenLab").permissions}
        self.assertEqual((permissions["Intendant OpenLab"].read, permissions["Intendant OpenLab"].write), (1, 0))


class TestPaiement(FrappeTestCase):
    def setUp(self):
        self.dossier = dossier(cours()).insert(ignore_permissions=True).name

    def tearDown(self):
        frappe.db.rollback()

    def paiement(self, **autres):
        champs = {"doctype": "Paiement OpenLab", "dossier": self.dossier, "montant": 10000, "moyen": "cinetpay",
                  "reference": "TX1", "statut": "confirme"}
        champs.update(autres)
        return frappe.get_doc(champs).insert(ignore_permissions=True)

    def test_reference_unique_par_moyen(self):
        self.paiement()
        with self.assertRaises(frappe.UniqueValidationError):
            self.paiement()

    def test_meme_reference_autre_moyen_permise(self):
        self.paiement()
        self.paiement(moyen="virement")


class TestJournal(FrappeTestCase):
    def setUp(self):
        self.dossier = dossier(cours()).insert(ignore_permissions=True).name
        self.entree = frappe.get_doc({"doctype": "Journal Paiement OpenLab", "dossier": self.dossier,
                                      "acteur": "Administrator", "action": "dispense", "motif": "test"}
                                     ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_horodate_a_l_insertion(self):
        self.assertTrue(self.entree.horodatage)

    def test_non_modifiable(self):
        self.entree.motif = "autre"
        with self.assertRaisesRegex(frappe.ValidationError, "non modifiable"):
            self.entree.save(ignore_permissions=True)

    def test_non_supprimable(self):
        with self.assertRaisesRegex(frappe.ValidationError, "non modifiable"):
            self.entree.delete(ignore_permissions=True)


class TestRappel(FrappeTestCase):
    def setUp(self):
        self.dossier = dossier(cours()).insert(ignore_permissions=True).name

    def tearDown(self):
        frappe.db.rollback()

    def rappel(self, **autres):
        champs = {"doctype": "Rappel Paiement OpenLab", "dossier": self.dossier, "date_limite": "2026-11-10",
                  "jours_avant": 7, "canal": "email", "statut": "envoye"}
        champs.update(autres)
        return frappe.get_doc(champs).insert(ignore_permissions=True)

    def test_cle_d_idempotence(self):
        self.assertEqual(self.rappel().cle, f"{self.dossier}|2026-11-10|7|email")
        with self.assertRaises(frappe.UniqueValidationError):
            self.rappel()

    def test_autre_canal_permis(self):
        self.rappel()
        self.rappel(canal="sms")


class TestRoleIntendant(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_role_cree_avec_acces_bureau_et_idempotent(self):
        frappe.delete_doc("Role", "Intendant OpenLab", force=True, ignore_missing=True)
        install.preparer_roles()
        install.preparer_roles()
        self.assertEqual(frappe.db.get_value("Role", "Intendant OpenLab", "desk_access"), 1)


class TestPatchDispense(FrappeTestCase):
    def setUp(self):
        self.cours = cours()
        self.eleve = utilisateur()
        self.cohorte = frappe.get_doc({
            "doctype": "LMS Batch", "title": "Cohorte patch paiement", "published": 1, "medium": "Online",
            "start_date": "2026-11-02", "end_date": "2027-02-22", "start_time": "18:30:00", "end_time": "20:30:00",
            "timezone": "Africa/Abidjan", "description": "d", "batch_details": "d",
            "instructors": [{"instructor": "Administrator"}], "courses": [{"course": self.cours}],
        }).insert(ignore_permissions=True).name

    def tearDown(self):
        frappe.db.rollback()

    def inscrire(self, cohorte):
        return frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": cohorte, "member": self.eleve}
                              ).insert(ignore_permissions=True)

    def dossiers(self):
        return frappe.get_all("Dossier Paiement OpenLab", {"apprenant": self.eleve},
                              ["cours", "cohorte", "dispense", "frais_inscription", "prix_une_fois",
                               "prix_deux_tranches", "prix_mensuel"])

    def test_inscription_existante_dispensee_et_rejeu_sans_doublon(self):
        self.inscrire(self.cohorte)
        dispenser_inscriptions_existantes.execute()
        dispenser_inscriptions_existantes.execute()
        self.assertEqual(self.dossiers(), [frappe._dict(
            cours=self.cours, cohorte=self.cohorte, dispense=1, frais_inscription=0, prix_une_fois=0,
            prix_deux_tranches=0, prix_mensuel=0)])

    def test_dossier_existant_respecte(self):
        self.inscrire(self.cohorte)
        dossier(self.cours, cohorte=self.cohorte, dispense=0).insert(ignore_permissions=True)
        dispenser_inscriptions_existantes.execute()
        self.assertEqual([d.dispense for d in self.dossiers()], [0])

    def test_cohorte_sans_cours_ignoree(self):
        self.inscrire(self.cohorte)
        frappe.db.delete("Batch Course", {"parent": self.cohorte})
        dispenser_inscriptions_existantes.execute()
        self.assertEqual(self.dossiers(), [])
