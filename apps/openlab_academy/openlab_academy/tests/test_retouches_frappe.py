"""Retouches faites dans l'application : marquées à l'enregistrement, conservées à la republication.

Un parcours naît d'un fichier, mais tout ce qu'il publie reste modifiable dans l'application : le
contenu d'une séance, l'énoncé d'un challenge et son corrigé, les questions d'un quiz, la fiche du
parcours. Dès qu'une de ces pièces est retouchée en ligne, elle porte une case qui met la
republication en retrait pour elle seule. Décochée, le fichier reprend la main.
"""
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from openlab_academy.domain.parcours import Bloc
from openlab_academy.infrastructure import retouches_frappe as retouches
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.tests.test_exercices_frappe import module

TITRE = "Parcours retouche test"
CHAMP = retouches.CHAMP


def _parcours():
    from openlab_academy.tests.fabriques import parcours
    return parcours(title=TITRE, questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),))


class _Socle(FrappeTestCase):
    def setUp(self):
        self.depot = DepotFrappe(commit=False)
        self.cours = self.depot.creer(_parcours())

    def tearDown(self):
        frappe.db.rollback()

    def republier(self):
        self.depot.remplacer(self.cours, _parcours())

    def lecon(self):
        return frappe.get_doc("Course Lesson", {"course": self.cours, "title": ["like", "01 ·%"]})

    def devoir(self):
        return frappe.get_doc("LMS Assignment", {"course": self.cours, "title": ["like", "Livrable 01%"]})

    def questions(self):
        quiz = frappe.db.get_value("LMS Quiz", {"course": self.cours})
        return frappe.get_all("LMS Quiz Question", {"parent": quiz}, pluck="question", order_by="idx")


class TestLeconsRetouchees(_Socle):
    def retoucher(self, texte="Paragraphe écrit en ligne"):
        lecon = self.lecon()
        contenu = json.loads(lecon.content)
        contenu["blocks"].insert(0, {"type": "paragraph", "data": {"text": texte}})
        lecon.content = json.dumps(contenu)
        lecon.save(ignore_permissions=True)
        return lecon.name

    def test_publication_ne_marque_aucune_lecon(self):
        self.assertEqual(frappe.db.count("Course Lesson", {"course": self.cours, CHAMP: 1}), 0)
        self.republier()
        self.assertEqual(frappe.db.count("Course Lesson", {"course": self.cours, CHAMP: 1}), 0)

    def test_retouche_en_ligne_marquee(self):
        nom = self.retoucher()
        self.assertEqual(frappe.db.get_value("Course Lesson", nom, CHAMP), 1)

    def test_enregistrement_sans_changement_de_contenu_ne_marque_rien(self):
        lecon = self.lecon()
        lecon.title = lecon.title  # un autre champ enregistré, contenu intact
        lecon.save(ignore_permissions=True)
        self.assertFalse(frappe.db.get_value("Course Lesson", lecon.name, CHAMP))

    def test_republication_conserve_le_contenu_retouche(self):
        self.retoucher()
        self.republier()
        lecon = self.lecon()
        blocs = json.loads(lecon.content)["blocks"]
        self.assertEqual(blocs[0], {"type": "paragraph", "data": {"text": "Paragraphe écrit en ligne"}})
        self.assertEqual(lecon.get(CHAMP), 1)

    def test_exercices_du_contenu_retouche_repointes(self):
        self.retoucher()
        # les devoirs reçoivent un identifiant neuf à chaque création, le quiz garde le sien (dérivé du titre)
        anciens = set(frappe.get_all("LMS Assignment", {"course": self.cours}, pluck="name"))
        self.republier()
        contenu = self.lecon().content
        for ancien in anciens:
            self.assertNotIn(ancien, contenu)
        nouveaux = {b["data"].get("quiz") or b["data"].get("assignment")
                    for b in json.loads(contenu)["blocks"] if b["type"] in ("quiz", "assignment")}
        self.assertTrue(nouveaux)
        for nom in nouveaux:
            self.assertTrue(frappe.db.exists("LMS Quiz", nom) or frappe.db.exists("LMS Assignment", nom))

    def test_case_decochee_le_fichier_reprend_la_main(self):
        nom = self.retoucher()
        frappe.db.set_value("Course Lesson", nom, CHAMP, 0)
        self.republier()
        self.assertNotIn("Paragraphe écrit en ligne", self.lecon().content)

    def test_une_autre_lecon_reste_regeneree(self):
        self.retoucher()
        self.republier()
        enonce = frappe.get_doc("Course Lesson", {"course": self.cours, "title": ["like", "Énoncé%"]})
        self.assertNotIn("Paragraphe écrit en ligne", enonce.content)
        self.assertFalse(enonce.get(CHAMP))


class TestDevoirsRetouches(_Socle):
    def retoucher(self):
        devoir = self.devoir()
        devoir.question = "<p>Consigne réécrite dans l'application</p>"
        devoir.answer = "<p>Corrigé type saisi en ligne</p>"
        devoir.save(ignore_permissions=True)
        return devoir.name

    def test_retouche_marquee(self):
        self.assertFalse(frappe.db.get_value("LMS Assignment", self.devoir().name, CHAMP))
        nom = self.retoucher()
        self.assertEqual(frappe.db.get_value("LMS Assignment", nom, CHAMP), 1)

    def test_republication_conserve_la_consigne_et_le_corrige(self):
        self.retoucher()
        self.republier()
        devoir = self.devoir()
        self.assertEqual(devoir.question, "<p>Consigne réécrite dans l'application</p>")
        self.assertEqual(devoir.answer, "<p>Corrigé type saisi en ligne</p>")
        self.assertEqual(devoir.get(CHAMP), 1)

    def test_case_decochee_le_fichier_reprend_la_main(self):
        nom = self.retoucher()
        frappe.db.set_value("LMS Assignment", nom, CHAMP, 0)
        self.republier()
        self.assertNotIn("réécrite dans l'application", self.devoir().question)

    def test_un_autre_devoir_reste_regenere(self):
        self.retoucher()
        self.republier()
        cas = frappe.get_doc("LMS Assignment", {"course": self.cours, "title": ["like", "Mise en situation%"]})
        self.assertNotIn("réécrite dans l'application", cas.question)

    def test_la_grille_du_devoir_conserve_reste_posee(self):
        from openlab_academy.infrastructure import depot_copies_frappe
        self.retoucher()
        self.republier()
        self.assertTrue(depot_copies_frappe.a_une_grille(self.devoir().name))


class TestQuestionsRetouchees(_Socle):
    def retoucher(self):
        nom = self.questions()[1]
        question = frappe.get_doc("LMS Question", nom)
        question.question = "Énoncé réécrit dans l'application ?"
        question.option_2 = "Réponse corrigée en ligne"
        question.save(ignore_permissions=True)
        return nom

    def test_retouche_marquee(self):
        nom = self.retoucher()
        self.assertEqual(frappe.db.get_value("LMS Question", nom, CHAMP), 1)

    def test_republication_conserve_la_question(self):
        self.retoucher()
        self.republier()
        deuxieme = frappe.get_doc("LMS Question", self.questions()[1])
        self.assertEqual(deuxieme.question, "Énoncé réécrit dans l'application ?")
        self.assertEqual(deuxieme.option_2, "Réponse corrigée en ligne")
        self.assertEqual(deuxieme.get(CHAMP), 1)

    def test_les_autres_questions_restent_regenerees(self):
        self.retoucher()
        self.republier()
        premiere = frappe.get_doc("LMS Question", self.questions()[0])
        self.assertNotIn("réécrit dans l'application", premiere.question)
        self.assertEqual(len(self.questions()), 5)

    def test_case_decochee_le_fichier_reprend_la_main(self):
        nom = self.retoucher()
        frappe.db.set_value("LMS Question", nom, CHAMP, 0)
        self.republier()
        self.assertNotIn("réécrit dans l'application", frappe.get_doc("LMS Question", self.questions()[1]).question)


class TestFicheDuParcoursRetouchee(_Socle):
    def retoucher(self):
        cours = frappe.get_doc("LMS Course", self.cours)
        cours.description = "<p>Présentation réécrite dans l'application</p>"
        cours.short_introduction = "Accroche revue en ligne"
        cours.save(ignore_permissions=True)

    def test_retouche_marquee(self):
        self.retoucher()
        self.assertEqual(frappe.db.get_value("LMS Course", self.cours, CHAMP), 1)

    def test_republication_conserve_la_fiche(self):
        self.retoucher()
        self.republier()
        cours = frappe.get_doc("LMS Course", self.cours)
        self.assertEqual(cours.description, "<p>Présentation réécrite dans l'application</p>")
        self.assertEqual(cours.short_introduction, "Accroche revue en ligne")

    def test_les_seances_restent_republiees(self):
        """La fiche conservée ne gèle pas le programme : les séances, elles, sont réécrites."""
        self.retoucher()
        self.republier()
        self.assertTrue(frappe.db.count("Course Lesson", {"course": self.cours}))
        self.assertFalse(frappe.db.get_value("Course Lesson", {"course": self.cours}, CHAMP))

    def test_case_decochee_le_fichier_reprend_la_main(self):
        self.retoucher()
        frappe.db.set_value("LMS Course", self.cours, CHAMP, 0)
        self.republier()
        self.assertNotIn("réécrite dans l'application",
                         frappe.db.get_value("LMS Course", self.cours, "description"))

    def test_publication_ne_marque_pas_le_parcours(self):
        self.republier()
        self.assertFalse(frappe.db.get_value("LMS Course", self.cours, CHAMP))
