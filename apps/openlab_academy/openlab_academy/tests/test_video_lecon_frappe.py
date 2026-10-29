"""Vidéo d'une leçon : insérée en tête du contenu servi par get_lesson, sans écriture en base ; lien refusé ignoré."""
import json

import frappe
from frappe.tests.utils import FrappeTestCase
from lms.lms import utils as lms_utils

from openlab_academy.domain.parcours import Bloc
from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.visibilite_frappe import CHAMP_VIDEO
from openlab_academy.tests.fabriques import parcours
from openlab_academy.tests.test_exercices_frappe import module

YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class TestVideoLecon(FrappeTestCase):
    def setUp(self):
        from openlab_academy.domain.reglages import Reglages
        self.cours = DepotFrappe(commit=False, reglages=Reglages()).creer(
            parcours(title="Parcours vidéo test", questions_par_quiz=5, blocs=(Bloc("B1", (module(),)),)))
        self.lecon = frappe.db.get_value("Course Lesson", {"course": self.cours, "title": ["like", "01 ·%"]})

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def poser(self, video):
        frappe.db.set_value("Course Lesson", self.lecon, CHAMP_VIDEO, video)

    def test_lecon_avec_video_commence_par_le_bloc(self):
        self.poser(YOUTUBE)
        details = lms.get_lesson(self.cours, 1, 1)
        blocs = json.loads(details["content"])["blocks"]
        self.assertEqual(blocs[0]["type"], "embed")
        self.assertEqual(blocs[0]["data"]["embed"], "dQw4w9WgXcQ")
        brut = json.loads(lms_utils.get_lesson(self.cours, 1, 1)["content"])["blocks"]
        self.assertEqual(blocs[1:], brut)
        self.assertNotIn("dQw4w9WgXcQ", frappe.db.get_value("Course Lesson", self.lecon, "content"))  # rien écrit

    def test_fichier_video_en_tete(self):
        self.poser("/files/intro.mp4")
        blocs = json.loads(lms.get_lesson(self.cours, 1, 1)["content"])["blocks"]
        self.assertEqual(blocs[0], {"type": "upload", "data": {
            "file_url": "/files/intro.mp4", "file_type": "mp4", "quizzes": []}})

    def test_lecon_sans_video_inchangee(self):
        self.assertEqual(lms.get_lesson(self.cours, 1, 1)["content"], lms_utils.get_lesson(self.cours, 1, 1)["content"])

    def test_lien_refuse_ignore(self):
        for lien in ("javascript:alert(1)", "http://exemple.ci/v.mp4", "https://evil.com/watch?v=dQw4w9WgXcQ"):
            with self.subTest(lien=lien):
                self.poser(lien)
                details = lms.get_lesson(self.cours, 1, 1)
                self.assertEqual(details["content"], lms_utils.get_lesson(self.cours, 1, 1)["content"])
                self.assertNotIn(lien, json.dumps(details, default=str))
