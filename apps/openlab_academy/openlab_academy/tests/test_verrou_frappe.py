"""Verrou d'accès aux exercices appliqué côté serveur sur de vraies soumissions LMS."""
import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from openlab_academy import hooks
from openlab_academy.domain.parcours import Bloc
from openlab_academy.domain.reglages import Reglages
from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import DepotOuverturesFrappe
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_blocage_frappe import sans_phase_de_lancement
from openlab_academy.tests.test_exercices_frappe import module

ELEVE = "eleve.verrou@example.ci"
NOTE = {"score": 5, "score_out_of": 5, "percentage": 100, "passing_percentage": 100}


class TestVerrouExercices(FrappeTestCase):
    def setUp(self):
        sans_phase_de_lancement(self)
        lms.vider_cache()
        if not frappe.db.exists("User", ELEVE):
            frappe.get_doc({"doctype": "User", "email": ELEVE, "first_name": "Aya", "send_welcome_email": 0,
                            "roles": [{"role": "LMS Student"}]}).insert(ignore_permissions=True)
        p = parcours(title="Parcours verrou test", questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),))
        self.cours = DepotFrappe(commit=False, reglages=Reglages()).creer(p)
        frappe.get_doc({"doctype": "LMS Enrollment", "course": self.cours, "member": ELEVE,
                        "member_type": "Student"}).insert(ignore_permissions=True)
        self.lecon = frappe.db.get_value("Course Lesson", {"course": self.cours, "title": ["like", "01 ·%"]})
        self.quiz = frappe.db.get_value("LMS Quiz", {"course": self.cours})
        devoirs = frappe.get_all("LMS Assignment", {"course": self.cours}, ["name", "title"])
        self.cas = next(d.name for d in devoirs if d.title.startswith("Mise en situation"))
        self.livrable = next(d.name for d in devoirs if d.title.startswith("Livrable"))

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def soumettre_quiz(self):
        return frappe.get_doc({"doctype": "LMS Quiz Submission", "quiz": self.quiz, "member": ELEVE,
                               "course": self.cours, **NOTE}).insert(ignore_permissions=True)

    def soumettre_devoir(self, devoir, reponse="Ma réponse argumentée"):
        return frappe.get_doc({"doctype": "LMS Assignment Submission", "assignment": devoir, "member": ELEVE,
                               "answer": reponse}).insert(ignore_permissions=True)

    def ouvrir(self, il_y_a_minutes):
        DepotOuverturesFrappe().enregistrer(ELEVE, self.lecon,
                                            now_datetime() - datetime.timedelta(minutes=il_y_a_minutes))

    def test_hooks_declares(self):
        self.assertEqual(hooks.override_whitelisted_methods["lms.lms.utils.get_lesson"],
                         "openlab_academy.entrypoints.lms.get_lesson")
        self.assertEqual(hooks.doc_events["LMS Quiz Submission"]["before_insert"],
                         "openlab_academy.entrypoints.lms.avant_soumission_quiz")
        self.assertEqual(hooks.doc_events["LMS Assignment Submission"]["before_insert"],
                         "openlab_academy.entrypoints.lms.avant_soumission_devoir")

    def test_ouverture_de_lecon_enregistree_par_la_surcharge(self):
        frappe.set_user(ELEVE)
        details = lms.get_lesson(self.cours, 1, 1)
        self.assertEqual(details["name"], self.lecon)
        self.assertIsNotNone(DepotOuverturesFrappe().premiere_ouverture(ELEVE, self.lecon))

    def test_anonyme_non_enregistre(self):
        frappe.set_user("Guest")
        lms.get_lesson(self.cours, 1, 1)
        frappe.set_user("Administrator")
        self.assertFalse(frappe.db.exists("Ouverture Lecon OpenLab", {"apprenant": "Guest"}))

    def test_quiz_refuse_avant_une_heure(self):
        self.ouvrir(il_y_a_minutes=20)
        frappe.set_user(ELEVE)
        with self.assertRaisesRegex(frappe.ValidationError, "encore 40 minutes"):
            self.soumettre_quiz()

    def test_quiz_refuse_si_lecon_jamais_ouverte(self):
        frappe.set_user(ELEVE)
        with self.assertRaisesRegex(frappe.ValidationError, "ouvrez d'abord la leçon"):
            self.soumettre_quiz()

    def test_intendant_jamais_verrouille(self):
        email = "intendant.verrou@example.ci"
        frappe.get_doc({"doctype": "User", "email": email, "first_name": "Ina", "send_welcome_email": 0,
                        "roles": [{"role": "Intendant OpenLab"}]}).insert(ignore_permissions=True)
        self.assertIn("Intendant OpenLab", lms.ROLES_NON_BLOQUES)
        lms._verifier(email, self.lecon)  # leçon jamais ouverte : un apprenant serait refusé
        with self.assertRaisesRegex(frappe.ValidationError, "ouvrez d'abord la leçon"):
            lms._verifier(ELEVE, self.lecon)

    def test_quiz_accepte_apres_une_heure(self):
        self.ouvrir(il_y_a_minutes=61)
        frappe.set_user(ELEVE)
        self.assertTrue(self.soumettre_quiz().name)

    def test_mise_en_situation_verrouillee_mais_pas_le_livrable(self):
        self.ouvrir(il_y_a_minutes=5)
        frappe.set_user(ELEVE)
        with self.assertRaisesRegex(frappe.ValidationError, "encore 55 minutes"):
            self.soumettre_devoir(self.cas)
        self.assertTrue(self.soumettre_devoir(self.livrable, "https://github.com/aya/livrable").name)

    def test_formateur_non_bloque(self):
        self.assertTrue(frappe.get_doc({"doctype": "LMS Quiz Submission", "quiz": self.quiz,
                                        "member": "Administrator", "course": self.cours, **NOTE}).insert(
            ignore_permissions=True).name)

    def test_journal_des_ouvertures_protege(self):
        """OWASP A01 : un apprenant ne peut ni lire ni falsifier les ouvertures (et donc avancer son déblocage)."""
        frappe.set_user(ELEVE)
        self.assertFalse(frappe.has_permission("Ouverture Lecon OpenLab", "read"))
        self.assertFalse(frappe.has_permission("Ouverture Lecon OpenLab", "create"))
