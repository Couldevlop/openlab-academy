"""Parcours « Bases de Python, jour après jour » : trente-cinq journées, deux leçons par journée.

La structure est l'essentiel du parcours : chaque journée s'ouvre par un rappel à quiz seul, qui verrouille
la leçon du jour, et se ferme par un challenge à rendre, qui verrouille le lendemain. Une pièce d'évaluation
posée au mauvais endroit bloque l'apprenant sur un rendu que la page ne demande pas ; ces invariants le
disent avant la publication.
"""
import pathlib
import unittest

from openlab_academy.domain.parcours import Evaluations, Parcours
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

TITRE = "Bases de Python, jour après jour"
JOURNEES = 35
RESSOURCES = pathlib.Path(__file__).parents[1] / "data" / "ressources"
BLOCS = 6


class TestParcoursPythonRh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trouves = [p for p in charger_dossier(PARCOURS_DIR) if p.title == TITRE]

    def setUp(self):
        self.assertEqual(len(self.trouves), 1)
        self.p = self.trouves[0]
        self.assertIsInstance(self.p, Parcours)
        self.modules = [m for b in self.p.blocs for m in b.modules]

    def test_six_blocs_et_soixante_neuf_lecons(self):
        """Trente-cinq journées, chacune avec son rappel, sauf la première qui n'a rien à rappeler."""
        self.assertEqual(len(self.p.blocs), BLOCS)
        self.assertEqual(len(self.modules), 2 * JOURNEES - 1)

    def test_rappel_puis_lecon_du_jour(self):
        attendus = ["J01"] + [f"J{j:02d}{suffixe}" for j in range(2, JOURNEES + 1) for suffixe in ("R", "")]
        self.assertEqual([m.num for m in self.modules], attendus)

    def test_pieces_d_evaluation_de_chaque_seance(self):
        """Le rappel ne porte qu'un quiz, la leçon du jour qu'un challenge : sinon la journée reste fermée."""
        for m in self.modules:
            with self.subTest(m.num):
                if m.num.endswith("R"):
                    self.assertEqual(m.evaluations, Evaluations.QUIZ)
                    self.assertEqual(m.livrable, "")
                    self.assertEqual(m.mise_en_situation, "")
                else:
                    self.assertEqual(m.evaluations, Evaluations.LIVRABLE)
                    self.assertTrue(m.livrable.strip())
                    self.assertEqual(m.quiz, ())

    def test_reglages_du_parcours(self):
        """Exercices ouverts tout de suite, tentatives généreuses sur le rappel, parcours payant et verrouillé."""
        self.assertEqual((self.p.delai_exercices_minutes, self.p.tentatives_max, self.p.score_min), (0, 10, 80))
        self.assertTrue(self.p.progression_sequentielle)
        self.assertFalse(self.p.gratuit)
        self.assertEqual((self.p.projets_attendus, self.p.portfolio), (0, ()))

    def test_capstone_sans_portfolio(self):
        self.assertEqual(self.p.capstone.titre, "Votre application RH, montrée à quelqu'un")
        self.assertIsNone(self.p.capstone.apres_module)

    def test_depot_du_jour_nomme_et_livre(self):
        """Le dépôt d'une journée est livré avec l'application ; les dépôts arrivent journée par journée (T8),
        donc le test porte sur ceux qui sont déjà cités."""
        for m in self.modules:
            if not m.archive:
                continue
            with self.subTest(m.num):
                self.assertEqual(m.archive, f"depot-python-{m.num.lower()}.zip")
                self.assertTrue((RESSOURCES / m.archive).is_file(), m.archive)

    def test_quiz_de_rappel_a_cinq_questions(self):
        """Les rappels se rédigent semaine par semaine ; celui qui porte un quiz le porte au complet."""
        for m in self.modules:
            if not m.quiz:
                continue
            with self.subTest(m.num):
                self.assertEqual(len(m.quiz), 5)
                for q in m.quiz:
                    self.assertEqual(len(q.options), 4)
                    self.assertEqual(len(q.bonnes), 1)
                    self.assertTrue(q.explication.strip())

    def test_aucun_texte_inacheve(self):
        for m in self.modules:
            for texte in (m.title, m.contenu, m.livrable):
                self.assertNotIn("TODO", texte)
