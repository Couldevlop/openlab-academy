import json

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.parcours import Bloc, Evaluations, Module
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import CHAMP_DELAI
from openlab_academy.tests.fabriques import parcours, question

TITRE = "Parcours exercices test"


def module(n_questions=5, num="01", **q):
    return Module(num, "M", "c", "l", quiz=tuple(question(**q) for _ in range(n_questions)),
                  mise_en_situation="Votre client vous appelle <b>urgence</b>")


def quiz_du_cours(cours):
    return frappe.get_all("LMS Quiz", {"course": cours}, pluck="name")


class TestPublicationExercices(FrappeTestCase):
    def setUp(self):
        self.reglages = Reglages(tentatives_max=3, score_min=100, delai_exercices_minutes=60)
        self.depot = DepotFrappe(commit=False, reglages=self.reglages)
        self.p = parcours(title=TITRE, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),))

    def tearDown(self):
        frappe.db.rollback()

    def lecon(self, cours):
        return frappe.get_doc("Course Lesson", {"course": cours, "title": ["like", "01 ·%"]})

    def test_quiz_lms_regle(self):
        cours = self.depot.creer(self.p)
        [nom] = quiz_du_cours(cours)
        quiz = frappe.get_doc("LMS Quiz", nom)
        lecon = self.lecon(cours)
        self.assertEqual((quiz.max_attempts, quiz.passing_percentage, quiz.lesson, quiz.show_answers),
                         (3, 100, lecon.name, 1))
        self.assertEqual((len(quiz.questions), quiz.total_marks), (5, 5))
        q = frappe.get_doc("LMS Question", quiz.questions[0].question)
        self.assertEqual((q.type, q.option_1, q.option_2, q.is_correct_1, q.is_correct_2), ("Choices", "a", "b", 0, 1))
        self.assertEqual(q.explanation_2, "Parce que b.")

    def test_lecon_embarque_quiz_cas_et_conseil(self):
        cours = self.depot.creer(self.p)
        lecon = self.lecon(cours)
        blocs = json.loads(lecon.content)["blocks"]
        types = [b["type"] for b in blocs]
        self.assertIn("quiz", types)
        self.assertEqual(blocs[types.index("quiz")]["data"], {"quiz": quiz_du_cours(cours)[0]})
        texte = json.dumps(blocs, ensure_ascii=False)
        self.assertIn("3 tentatives", texte)
        self.assertIn("100 %", texte)
        self.assertIn("relisez le cours", texte)
        self.assertIn("60 minutes", texte)
        self.assertIn("&lt;b&gt;urgence&lt;/b&gt;", texte)
        devoirs = [a.assessment_name for a in lecon.assessments if a.assessment_type == "LMS Assignment"]
        cas = frappe.get_doc("LMS Assignment", {"name": ["in", devoirs], "title": ["like", "Mise en situation%"]})
        self.assertEqual((cas.type, cas.title), ("Text", "Mise en situation 01 — M"))
        self.assertIn({"assessment_type": "LMS Quiz", "assessment_name": quiz_du_cours(cours)[0]},
                      [{"assessment_type": a.assessment_type, "assessment_name": a.assessment_name}
                       for a in lecon.assessments])

    def test_reglages_propres_au_parcours_appliques(self):
        """Le parcours règle ses exercices : le quiz LMS, la phrase de la leçon et le champ lu par le verrou."""
        p = parcours(title=TITRE, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),),
                     delai_exercices_minutes=15, tentatives_max=5, score_min=70)
        cours = self.depot.creer(p)
        [nom] = quiz_du_cours(cours)
        quiz = frappe.get_doc("LMS Quiz", nom)
        self.assertEqual((quiz.max_attempts, quiz.passing_percentage), (5, 70))
        texte = json.dumps(json.loads(self.lecon(cours).content)["blocks"], ensure_ascii=False)
        self.assertIn("15 minutes", texte)
        self.assertIn("5 tentatives", texte)
        self.assertIn("70 %", texte)
        self.assertEqual(frappe.db.get_value("LMS Course", cours, CHAMP_DELAI), 15)

    def test_delai_global_pose_sur_le_parcours_a_la_publication(self):
        """Fichier sans réglage propre : le délai de la plateforme est posé sur le parcours, modifiable ensuite
        dans l'application parcours par parcours."""
        cours = self.depot.creer(self.p)
        self.assertEqual(frappe.db.get_value("LMS Course", cours, CHAMP_DELAI), 60)

    def test_seance_de_livrable_seul_publiee_sans_quiz(self):
        """Séance de livrable seul : leçon publiée, aucun quiz ni mise en situation, livrable conservé."""
        p = parcours(title=TITRE, questions_par_quiz=5,
                     blocs=(Bloc("B1", (Module("01", "M", "c", "l", evaluations=Evaluations.LIVRABLE),
                                        module(num="02"))),))
        cours = self.depot.creer(p)
        self.assertEqual(len(quiz_du_cours(cours)), 1)
        lecon = self.lecon(cours)
        types = [b["type"] for b in json.loads(lecon.content)["blocks"]]
        self.assertNotIn("quiz", types)
        self.assertEqual([a.assessment_type for a in lecon.assessments], ["LMS Assignment"])
        self.assertTrue(frappe.db.exists("LMS Assignment", {"course": cours, "title": "Livrable 01 — M"}))
        self.assertFalse(frappe.db.exists("LMS Assignment", {"course": cours,
                                                             "title": ["like", "Mise en situation 01%"]}))

    def test_seance_de_quiz_seul_publiee_sans_devoir(self):
        """Rappel du matin : le quiz est posé, et aucun devoir n'attend un rendu que la séance ne demande pas."""
        p = parcours(title=TITRE, questions_par_quiz=5,
                     blocs=(Bloc("B1", (Module("01", "M", "c", "",
                                               quiz=tuple(question() for _ in range(5)),
                                               evaluations=Evaluations.QUIZ),)),))
        cours = self.depot.creer(p)
        self.assertEqual(len(quiz_du_cours(cours)), 1)
        lecon = self.lecon(cours)
        self.assertEqual([a.assessment_type for a in lecon.assessments], ["LMS Quiz"])
        self.assertFalse(frappe.db.exists("LMS Assignment", {"course": cours, "title": ["like", "%01 — M"]}))
        self.assertNotIn("Livrable", lecon.content)
        self.assertNotIn("Format :", lecon.content)

    def test_seance_sans_evaluation_publiee_nue(self):
        """Lecture du soir : ni quiz ni devoir, et la leçon reste publiée."""
        p = parcours(title=TITRE, questions_par_quiz=5,
                     blocs=(Bloc("B1", (Module("01", "M", "c", "", evaluations=Evaluations.AUCUNE),
                                        module(num="02"))),))
        cours = self.depot.creer(p)
        lecon = self.lecon(cours)
        self.assertEqual(list(lecon.assessments), [])
        self.assertFalse(frappe.db.exists("LMS Assignment", {"course": cours, "title": ["like", "%01 — M"]}))

    def test_choix_multiple(self):
        p = parcours(title=TITRE, questions_par_quiz=5, blocs=(Bloc("B1", (module(bonnes=(1, 3)),)),))
        cours = self.depot.creer(p)
        q = frappe.get_doc("LMS Question", frappe.get_doc("LMS Quiz", quiz_du_cours(cours)[0]).questions[0].question)
        self.assertEqual((q.multiple, q.is_correct_1, q.is_correct_3), (1, 1, 1))

    def test_xss_neutralise_dans_les_questions(self):
        """OWASP A03."""
        p = parcours(title=TITRE, questions_par_quiz=5,
                     blocs=(Bloc("B1", (module(enonce="<script>x</script> ?", options=("<img src=x>", "b")),)),))
        cours = self.depot.creer(p)
        q = frappe.get_doc("LMS Question", frappe.get_doc("LMS Quiz", quiz_du_cours(cours)[0]).questions[0].question)
        self.assertNotIn("<script>", q.question)
        self.assertNotIn("<img", q.option_1)

    def test_republication_sans_orphelins(self):
        cours = self.depot.creer(self.p)
        avant = frappe.db.count("LMS Question")
        self.depot.remplacer(cours, self.p)
        self.assertEqual(len(quiz_du_cours(cours)), 1)
        self.assertEqual(frappe.db.count("LMS Question"), avant)

    def test_republication_avec_quiz_vide_ajoute_a_la_main(self):
        cours = self.depot.creer(self.p)
        frappe.get_doc({"doctype": "LMS Quiz", "title": "Quiz manuel vide", "course": cours}).insert(
            ignore_permissions=True)
        self.depot.remplacer(cours, self.p)
        self.assertEqual(len(quiz_du_cours(cours)), 1)

    def test_sans_exercices_si_non_exiges(self):
        cours = self.depot.creer(parcours(title=TITRE))
        self.assertEqual(quiz_du_cours(cours), [])
        self.assertNotIn('"quiz"', self.lecon(cours).content)
