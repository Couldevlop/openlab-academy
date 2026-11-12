"""Parcours de lancement « IA agentique » : fichier livré complet, gratuit, ouvert sur la cohorte, mis en avant."""
import unittest

from openlab_academy.domain.parcours import Parcours
from openlab_academy.domain.reglages import TITRE_LANCEMENT
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

TITRE = TITRE_LANCEMENT
MODULES = [
    ("01", "Anatomie d'un agent IA"),
    ("02", "Tool calling et boucle d'agent"),
    ("03", "Patterns d'orchestration"),
    ("04", "État, mémoire et reprise sur erreur"),
    ("05", "MCP et interopérabilité"),
    ("06", "Architectures multi-agents et A2A"),
    ("07", "Sécurité, évaluation et observabilité"),
]


def _textes(p: Parcours):
    yield from (p.title, p.short_introduction, p.description, *p.tags)
    for bloc in p.blocs:
        yield bloc.title
        for m in bloc.modules:
            yield from (m.num, m.title, m.contenu, m.livrable, m.mise_en_situation)
            for q in m.quiz:
                yield from (q.enonce, q.explication, *q.options)
    c = p.capstone
    yield from (c.titre, c.contexte, *c.objectifs, *c.fonctionnalites, *c.stack, *c.criteres_acceptation,
                *c.exigences_specifiques, *c.livrables)


class TestParcoursIaAgentique(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trouves = [p for p in charger_dossier(PARCOURS_DIR) if p.title == TITRE]

    def setUp(self):
        self.assertEqual(len(self.trouves), 1)
        self.p = self.trouves[0]
        self.assertIsInstance(self.p, Parcours)

    def test_cles_de_lancement(self):
        self.assertEqual((self.p.gratuit, self.p.acces_limite_a_la_cohorte, self.p.mise_en_avant), (True, True, True))

    def test_sept_modules_dans_l_ordre(self):
        modules = [(m.num, m.title) for b in self.p.blocs for m in b.modules]
        self.assertEqual(modules, MODULES)

    def test_exercices_et_fil_rouge(self):
        for n, m in enumerate((m for b in self.p.blocs for m in b.modules), start=1):
            with self.subTest(m.num):
                self.assertEqual(len(m.quiz), 5)
                self.assertTrue(m.mise_en_situation.strip())
                self.assertTrue(m.livrable.startswith(f"Étape {n} :"), m.livrable)
                for q in m.quiz:
                    self.assertEqual(len(q.options), 4)
                    self.assertEqual(len(q.bonnes), 1)

    def test_charge_et_capstone(self):
        self.assertEqual(self.p.portfolio, ())
        self.assertEqual(self.p.heures_par_module, 3)
        self.assertEqual(self.p.charge_horaire(), 24)
        self.assertEqual(self.p.capstone.titre, "Projet final et revue technique")

    def test_aucun_texte_inacheve(self):
        for texte in _textes(self.p):
            self.assertNotIn("TODO", texte)
            self.assertNotIn("…", texte)
