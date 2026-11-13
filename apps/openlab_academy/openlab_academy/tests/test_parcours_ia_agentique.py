"""Parcours de lancement « IA agentique » : fichier livré complet, gratuit, ouvert sur la cohorte, mis en avant."""
import unittest

from openlab_academy.domain.parcours import Parcours
from openlab_academy.domain.reglages import TITRE_LANCEMENT
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

TITRE = TITRE_LANCEMENT
MODULES = [
    ("01", "Histoire de l'IA agentique, de 1966 à aujourd'hui"),
    ("02", "Les modèles de langage, de l'intérieur"),
    ("03", "Le prompting, pratiques qui tiennent à la mesure"),
    ("04", "Anatomie d'un agent IA"),
    ("05", "Tool calling et boucle d'agent"),
    ("06", "L'orchestrateur sans framework"),
    ("07", "Brancher un vrai modèle sur votre boucle"),
    ("08", "État, mémoire et reprise sur erreur"),
    ("09", "Mémoire longue et recherche documentaire"),
    ("10", "Le même orchestrateur avec LangGraph"),
    ("11", "CrewAI, PydanticAI et GenAI, puis le comparatif"),
    ("12", "MCP et interopérabilité"),
    ("13", "Architectures multi-agents et A2A"),
    ("14", "Sécurité, évaluation et observabilité"),
    ("15", "Empaqueter et déployer par pipeline"),
    ("16", "Exploiter l'agent en production"),
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

    def test_modules_dans_l_ordre(self):
        modules = [(m.num, m.title) for b in self.p.blocs for m in b.modules]
        self.assertEqual(modules, MODULES)

    def test_exercices_et_fil_rouge(self):
        for m in (m for b in self.p.blocs for m in b.modules):
            with self.subTest(m.num):
                self.assertEqual(len(m.quiz), 5)
                self.assertTrue(m.mise_en_situation.strip())
                # le livrable porte le numéro de la séance : les séances se lisent dans l'ordre du dépôt
                self.assertTrue(m.livrable.startswith(f"Étape {int(m.num)} :"), m.livrable)
                for q in m.quiz:
                    self.assertEqual(len(q.options), 4)
                    self.assertEqual(len(q.bonnes), 1)

    def test_charge_et_capstone(self):
        self.assertEqual(self.p.portfolio, ())
        self.assertEqual(self.p.heures_par_module, 3)
        self.assertEqual(self.p.charge_horaire(), 3 * len(MODULES) + self.p.capstone.duree_h)
        self.assertEqual(self.p.capstone.titre, "Projet final et revue technique")

    def test_aucun_texte_inacheve(self):
        for texte in _textes(self.p):
            self.assertNotIn("TODO", texte)
            self.assertNotIn("…", texte)
