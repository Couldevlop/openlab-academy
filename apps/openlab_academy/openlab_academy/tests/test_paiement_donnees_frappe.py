"""Données du paiement : tarifs, réglages, dossiers, paiements, journal, rappels, rôle Intendant, patch de dispense."""
import datetime
from unittest import mock

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


def inscrire_sans_paiement(lot, membre):
    """Inscription d'un autre test : tarif du parcours posé si absent, date figée au début de la cohorte, dossier
    dispensé (sinon les frais d'inscription impayés bloqueraient le parcours, selon l'ordre des tests)."""
    from openlab_academy.entrypoints import lms, paiement
    c = frappe.db.get_value("Batch Course", {"parent": lot}, "course", order_by="idx")
    if not frappe.db.exists("Tarif Parcours OpenLab", c):
        tarif(c).insert(ignore_permissions=True)
    debut = frappe.utils.getdate(frappe.db.get_value("LMS Batch", lot, "start_date"))
    with mock.patch.object(paiement, "jour_courant", return_value=debut):
        inscription = frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": lot, "member": membre}).insert(
            ignore_permissions=True)
    frappe.db.set_value("Dossier Paiement OpenLab", {"apprenant": membre, "cours": c}, "dispense", 1)
    lms.vider_cache()
    return inscription


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


DROITS = ("select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import",
          "share", "print", "email", "if_owner")


def droits(doctype: str, ajoutees: bool = False) -> set:
    """Règles de LMS Course (rôle, niveau, droits), hors règles ajoutées par l'application si `ajoutees` : choix du
    parcours par l'intendant, case « Parcours gratuit » de l'administrateur. Une montée de LMS qui change ses droits
    standard fait échouer la comparaison : les droits personnalisés, figés, sont alors à reprendre."""
    regles = frappe.get_all(doctype, {"parent": "LMS Course"}, ["role", "permlevel", *DROITS])
    if ajoutees:
        regles = [r for r in regles if not (r.role == "Intendant OpenLab" and r.permlevel == 0)
                  and not (r.role == "System Manager" and r.permlevel == 1)]
    return {(r.role, r.permlevel, *(r[d] or 0 for d in DROITS)) for r in regles}


class TestRoleIntendant(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_role_cree_avec_acces_bureau_et_idempotent(self):
        frappe.delete_doc("Role", "Intendant OpenLab", force=True, ignore_missing=True)
        install.preparer_roles()
        install.preparer_roles()
        self.assertEqual(frappe.db.get_value("Role", "Intendant OpenLab", "desk_access"), 1)

    def test_l_intendant_choisit_le_parcours_d_un_tarif_sans_lire_les_parcours(self):
        frappe.db.delete("Custom DocPerm", {"parent": "LMS Course", "role": "Intendant OpenLab"})
        install.preparer_roles()
        install.preparer_roles()
        (regle,) = frappe.get_all("Custom DocPerm", {"parent": "LMS Course", "role": "Intendant OpenLab"},
                                  ["select", "read", "write"])
        self.assertEqual((regle.select, regle.read, regle.write), (1, 0, 0))
        # les droits standard restent en vigueur, à l'identique (recopiés avant les règles ajoutées)
        self.assertEqual(droits("Custom DocPerm", ajoutees=True), droits("DocPerm"))
        intendant = utilisateur("tarifs.intendant@example.ci")
        frappe.get_doc("User", intendant).add_roles("Intendant OpenLab")
        nom = cours("Parcours choisi par l'intendant")
        frappe.set_user(intendant)
        try:
            self.assertTrue(frappe.has_permission("LMS Course", "select"))
            self.assertFalse(frappe.has_permission("LMS Course", "read"))
            from frappe.desk.search import search_link
            self.assertIn(nom, [r["value"] for r in search_link("LMS Course", "choisi par l")])
        finally:
            frappe.set_user("Administrator")


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
        """Inscription antérieure au paiement : les points d'accroche de l'inscription sont neutralisés."""
        from openlab_academy.entrypoints import paiement
        with mock.patch.object(paiement, "avant_inscription"), mock.patch.object(paiement, "apres_inscription"):
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
