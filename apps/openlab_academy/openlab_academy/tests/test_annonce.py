import pathlib
import tempfile
import unittest

import frappe
import yaml
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.publier_parcours import PublierParcours, Statut
from openlab_academy.domain.parcours import Annonce, ParcoursInvalide
from openlab_academy.entrypoints import seed
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.yaml_source import FormatInvalide, depuis_dict
from openlab_academy.tests.fabriques import parcours, parcours_brut
from openlab_academy.tests.test_publier_parcours import DepotEnMemoire

TITRE = "Parcours annoncé test"


def annonce(**autres):
    champs = dict(title=TITRE, short_introduction="Bientôt", description="<p>Description</p>", tags=("x",),
                  card_gradient="Red")
    champs.update(autres)
    return Annonce(**champs)


def annonce_brute(**autres):
    brut = {"statut": "a_venir", "title": TITRE, "short_introduction": "Bientôt",
            "description": "<p>Description</p>", "tags": ["x"], "card_gradient": "Red"}
    brut.update(autres)
    return brut


class TestAnnonceDomaine(unittest.TestCase):
    def test_remuneration_interdite(self):
        with self.assertRaisesRegex(ParcoursInvalide, "description: rémunération en k€ interdite"):
            annonce(description="Jusqu'à 70 k€")

    def test_titre_obligatoire(self):
        with self.assertRaisesRegex(ParcoursInvalide, "title manquant"):
            annonce(title=" ")


class TestAnnonceYaml(unittest.TestCase):
    def test_lecture_sans_contenu_pedagogique(self):
        a = depuis_dict(annonce_brute(), "c.yaml")
        self.assertIsInstance(a, Annonce)
        self.assertEqual((a.title, a.card_gradient, a.tags), (TITRE, "Red", ("x",)))

    def test_statut_inconnu_refuse(self):
        with self.assertRaisesRegex(FormatInvalide, r"c\.yaml: statut « brouillon » inconnu"):
            depuis_dict(annonce_brute(statut="brouillon"), "c.yaml")

    def test_champ_manquant_localise(self):
        brut = annonce_brute()
        del brut["short_introduction"]
        with self.assertRaisesRegex(FormatInvalide, r"c\.yaml: short_introduction manquant"):
            depuis_dict(brut, "c.yaml")

    def test_parcours_complet_par_defaut(self):
        self.assertNotIsInstance(depuis_dict(parcours_brut(), "t.yaml"), Annonce)


class TestAnnoncePublication(unittest.TestCase):
    def test_cas_d_usage_accepte_les_annonces(self):
        depot = DepotEnMemoire()
        self.assertEqual(PublierParcours(depot, print).executer([annonce()]), {TITRE: Statut.CREE})


class TestAnnonceFrappe(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_cours_a_venir_sans_chapitre(self):
        depot = DepotFrappe(commit=False)
        nom = depot.creer(annonce())
        cours = frappe.get_doc("LMS Course", nom)
        self.assertEqual((cours.upcoming, cours.published, len(cours.chapters)), (1, 1, 0))
        self.assertEqual(cours.short_introduction, "Bientôt")

    def test_annonce_remplacee_par_le_parcours_complet(self):
        depot = DepotFrappe(commit=False)
        nom = depot.creer(annonce())
        depot.remplacer(nom, parcours(title=TITRE))
        cours = frappe.get_doc("LMS Course", nom)
        self.assertEqual(cours.upcoming, 0)
        self.assertEqual(len(cours.chapters), 12)

    def test_seed_publie_les_annonces(self):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "c.yaml").write_text(yaml.safe_dump(annonce_brute(), allow_unicode=True), encoding="utf-8")
            self.assertEqual(seed.run(d, commit=False), {TITRE: "cree"})

    def test_parcours_cybersecurite_annonces(self):
        statuts = seed.run(commit=False)
        for titre in ("Ingénieur Cybersécurité I", "Ingénieur Cybersécurité II"):
            self.assertIn(statuts.get(titre), ("cree", "maj"))
            self.assertEqual(frappe.db.get_value("LMS Course", {"title": titre}, "upcoming"), 1)
