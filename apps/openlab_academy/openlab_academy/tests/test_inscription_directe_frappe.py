"""Inscription directe à un parcours (« Enroll Now » du LMS) : refusée sur un parcours payant, hors équipe et hors
cohorte ; la cohorte, le MOOC, l'équipe et l'administrateur passent. Case « inscription autonome désactivée » tenue
à jour, cohorte à plusieurs parcours payants refusée."""
import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy import hooks
from openlab_academy.entrypoints import lms
from openlab_academy.patches import fermer_autonomie_parcours_payants
from openlab_academy.tests.test_paiement_api_frappe import agent
from openlab_academy.tests.test_paiement_donnees_frappe import ELEVE, cours, tarif, utilisateur
from openlab_academy.tests.test_paiement_inscription_frappe import cohorte, dossier_de, inscrire
from openlab_academy.tests.test_parcours_gratuits_frappe import rendre

INSCRIPTION = "LMS Enrollment"
HORS_COHORTE = "Inscrivez-vous à une cohorte de ce parcours."


def autonomie_fermee(c) -> int:
    return frappe.db.get_value("LMS Course", c, "disable_self_learning")


class Base(FrappeTestCase):
    def setUp(self):
        utilisateur()
        lms.vider_cache()
        self.cours = cours("Parcours payant inscription directe")
        tarif(self.cours).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        lms.vider_cache()
        frappe.db.rollback()

    def s_inscrire(self, membre=ELEVE, c=None, **champs):
        """Comme le bouton « Enroll Now » (frappe.client.insert) : en session de l'apprenant, droits vérifiés."""
        frappe.set_user(membre)
        try:
            return frappe.get_doc({"doctype": INSCRIPTION, "course": c or self.cours, "member": membre,
                                   **champs}).insert()
        finally:
            frappe.set_user("Administrator")

    def inscrit(self, membre=ELEVE, c=None):
        return bool(frappe.db.exists(INSCRIPTION, {"course": c or self.cours, "member": membre}))


class TestInscriptionDirecte(Base):
    def test_hook_declare(self):
        self.assertEqual(hooks.doc_events[INSCRIPTION],
                         {"before_insert": "openlab_academy.entrypoints.paiement.avant_inscription_parcours"})

    def test_parcours_payant_refuse_meme_autonomie_rouverte(self):
        """Le refus ne dépend pas de la case du LMS : un administrateur peut la décocher."""
        frappe.db.set_value("LMS Course", self.cours, "disable_self_learning", 0)
        with self.assertRaisesRegex(frappe.ValidationError, HORS_COHORTE):
            self.s_inscrire()
        self.assertFalse(self.inscrit())
        self.assertIsNone(dossier_de(self.cours))
        self.assertFalse(lms.bloque_pour(ELEVE, self.cours))  # d'où le refus : sans dossier, rien ne bloquerait

    def test_parcours_payant_refuse_par_la_case_du_lms(self):
        self.assertEqual(autonomie_fermee(self.cours), 1)
        with self.assertRaises(frappe.ValidationError):
            self.s_inscrire()
        self.assertFalse(self.inscrit())

    def test_parcours_sans_tarif_refuse(self):
        c = cours("Parcours sans tarif inscription directe")
        frappe.db.set_value("LMS Course", c, "disable_self_learning", 0)
        with self.assertRaisesRegex(frappe.ValidationError, HORS_COHORTE):
            self.s_inscrire(c=c)

    def test_cohorte_designee_sans_y_etre_inscrit_refusee(self):
        frappe.db.set_value("LMS Course", self.cours, "disable_self_learning", 0)
        lot = cohorte(self.cours)
        with self.assertRaisesRegex(frappe.ValidationError, HORS_COHORTE):
            self.s_inscrire(enrollment_from_batch=lot)
        self.assertFalse(self.inscrit())

    def test_inscription_a_la_cohorte_inscrit_au_parcours_et_ouvre_le_dossier(self):
        lot = cohorte(self.cours)
        frappe.set_user(ELEVE)
        try:
            inscrire(lot)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(INSCRIPTION, {"course": self.cours, "member": ELEVE},
                                             "enrollment_from_batch"), lot)
        self.assertTrue(dossier_de(self.cours))

    def test_mooc_en_autonomie(self):
        rendre(self.cours)
        self.assertEqual(autonomie_fermee(self.cours), 0)
        self.s_inscrire()
        self.assertTrue(self.inscrit())
        self.assertIsNone(dossier_de(self.cours))

    def test_equipe_en_autonomie(self):
        """Le paiement ne refuse jamais l'équipe ; la case du LMS reste, elle, le choix de l'administrateur."""
        frappe.db.set_value("LMS Course", self.cours, "disable_self_learning", 0)
        for role in ("Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"):
            email = agent(f"{role.split()[0].lower()}.autonomie@example.ci", role)
            frappe.get_doc("User", email).add_roles("LMS Student")
            with self.subTest(role=role):
                frappe.set_user(email)
                try:
                    frappe.get_doc({"doctype": INSCRIPTION, "course": self.cours, "member": email}).insert(
                        ignore_permissions=True)
                finally:
                    frappe.set_user("Administrator")
                self.assertTrue(self.inscrit(email))

    def test_administrateur_qui_inscrit_un_apprenant(self):
        frappe.get_doc({"doctype": INSCRIPTION, "course": self.cours, "member": ELEVE}).insert(
            ignore_permissions=True)
        self.assertTrue(self.inscrit())

    def test_ni_l_intendant_ni_le_createur_n_inscrivent_hors_cohorte(self):
        frappe.db.set_value("LMS Course", self.cours, "disable_self_learning", 0)
        for role in ("Intendant OpenLab", "Course Creator"):
            email = agent(f"{role.split()[0].lower()}.inscrit@example.ci", role)
            with self.subTest(role=role):
                frappe.set_user(email)
                try:
                    with self.assertRaisesRegex(frappe.ValidationError, HORS_COHORTE):
                        frappe.get_doc({"doctype": INSCRIPTION, "course": self.cours, "member": ELEVE}).insert(
                            ignore_permissions=True)
                finally:
                    frappe.set_user("Administrator")
        self.assertFalse(self.inscrit())


class TestAutonomie(Base):
    def test_parcours_payant_ferme_des_sa_creation(self):
        self.assertEqual(autonomie_fermee(self.cours), 1)

    def test_rouverte_quand_le_parcours_devient_gratuit_fermee_quand_il_redevient_payant(self):
        rendre(self.cours)
        self.assertEqual(autonomie_fermee(self.cours), 0)
        rendre(self.cours, False)
        self.assertEqual(autonomie_fermee(self.cours), 1)

    def test_choix_de_l_administrateur_respecte_sur_un_mooc(self):
        rendre(self.cours)
        doc = frappe.get_doc("LMS Course", self.cours)
        doc.disable_self_learning = 1
        doc.save(ignore_permissions=True)
        self.assertEqual(autonomie_fermee(self.cours), 1)

    def test_patch_ferme_les_parcours_payants_existants(self):
        mooc = cours("MOOC patch autonomie")
        rendre(mooc)
        frappe.db.set_value("LMS Course", self.cours, "disable_self_learning", 0)
        fermer_autonomie_parcours_payants.execute()
        fermer_autonomie_parcours_payants.execute()
        self.assertEqual((autonomie_fermee(self.cours), autonomie_fermee(mooc)), (1, 0))


class TestCohorteAPlusieursParcours(Base):
    def ajouter(self, lot, c):
        doc = frappe.get_doc("LMS Batch", lot)
        doc.append("courses", {"course": c})
        doc.save(ignore_permissions=True)

    def test_deux_parcours_payants_refuses(self):
        lot = cohorte(self.cours)
        autre = cours("Second parcours payant de la cohorte")
        tarif(autre).insert(ignore_permissions=True)
        self.ajouter(lot, autre)
        with self.assertRaisesRegex(frappe.ValidationError, "plusieurs parcours payants"):
            inscrire(lot)
        self.assertFalse(frappe.db.exists("LMS Batch Enrollment", {"batch": lot, "member": ELEVE}))

    def test_le_parcours_payant_porte_le_dossier_le_mooc_suit(self):
        mooc = cours("MOOC en tête de cohorte")
        rendre(mooc)
        lot = cohorte(mooc)
        self.ajouter(lot, self.cours)
        inscrire(lot)
        self.assertTrue(dossier_de(self.cours))
        self.assertIsNone(dossier_de(mooc))
        self.assertTrue(self.inscrit() and self.inscrit(c=mooc))
