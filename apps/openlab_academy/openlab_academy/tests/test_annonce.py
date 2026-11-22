import pathlib
import tempfile
import unittest

import frappe
import yaml
from frappe.tests.utils import FrappeTestCase

from openlab_academy.application.publier_parcours import PublierParcours, Statut
from openlab_academy.domain.parcours import Annonce, BlocAnnonce, ParcoursInvalide
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


class TestLeProgrammeAnnonce(unittest.TestCase):
    """Un parcours en conception ne peut donner à lire qu'un plan. Il doit tenir ce qu'il affiche."""

    def test_sans_programme_une_annonce_reste_valide(self):
        """Le plan est facultatif : annoncer un parcours n'oblige pas à en avoir déjà écrit le plan."""
        self.assertEqual(annonce().programme, ())
        self.assertEqual(annonce().seances, 0)

    def test_les_seances_sont_comptees_et_jamais_estimees(self):
        a = annonce(programme=(BlocAnnonce("Bloc 1", ("A", "B")), BlocAnnonce("Bloc 2", ("C",))))
        self.assertEqual(a.seances, 3)

    def test_un_bloc_sans_seance_est_refuse(self):
        """Un bloc vide se lit comme un oubli, et la page montrerait un titre qui ne mène nulle part."""
        with self.assertRaises(ParcoursInvalide):
            BlocAnnonce("Bloc creux", ())

    def test_un_bloc_sans_titre_est_refuse(self):
        with self.assertRaises(ParcoursInvalide):
            BlocAnnonce("   ", ("A",))

    def test_une_seance_sans_intitule_est_refusee(self):
        with self.assertRaises(ParcoursInvalide):
            BlocAnnonce("Bloc 1", ("A", "  "))

    def test_un_intitule_trop_long_pour_le_lms_est_refuse_des_le_domaine(self):
        """Le LMS coupe à 140 caractères : mieux vaut un refus lisible qu'un titre tronqué en base."""
        with self.assertRaises(ParcoursInvalide):
            BlocAnnonce("Bloc 1", ("x" * 121,))


class TestLeProgrammeAnnonceDepuisUnFichier(unittest.TestCase):
    def test_le_fichier_porte_blocs_et_seances(self):
        brut = {"statut": "a_venir", "title": TITRE, "short_introduction": "Bientôt",
                "description": "<p>d</p>", "tags": ["x"],
                "programme": [{"titre": "Bloc 1 — Fondations", "seances": ["01 · Rust", "02 · Cargo"]},
                              {"titre": "Bloc 2 — Concurrence", "seances": ["03 · Async"]}]}
        a = depuis_dict(brut, "essai.yaml")
        self.assertIsInstance(a, Annonce)
        self.assertEqual(a.seances, 3)
        self.assertEqual(a.programme[0].titre, "Bloc 1 — Fondations")
        self.assertEqual(a.programme[1].seances, ("03 · Async",))

    def test_un_fichier_sans_programme_reste_accepte(self):
        brut = {"statut": "a_venir", "title": TITRE, "short_introduction": "Bientôt",
                "description": "<p>d</p>", "tags": ["x"]}
        self.assertEqual(depuis_dict(brut, "essai.yaml").programme, ())

    def test_un_programme_mal_forme_est_refuse_avec_le_nom_du_fichier(self):
        """Le refus doit dire quel fichier reprendre : la publication en lit huit d'affilée."""
        brut = {"statut": "a_venir", "title": TITRE, "short_introduction": "Bientôt",
                "description": "<p>d</p>", "tags": ["x"], "programme": ["Bloc 1"]}
        with self.assertRaises(FormatInvalide) as e:
            depuis_dict(brut, "essai.yaml")
        self.assertIn("essai.yaml", str(e.exception))


class TestLeProgrammeAnnoncePublie(FrappeTestCase):
    """Le plan doit arriver jusqu'à la fiche, et rien ne doit y être ouvrable."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.depot = DepotFrappe(commit=False)

    def tearDown(self):
        frappe.db.rollback()

    def test_les_blocs_annonces_deviennent_des_chapitres_et_des_seances_sans_contenu(self):
        a = annonce(title="Annoncé avec plan",
                    programme=(BlocAnnonce("Bloc 1 — Fondations", ("01 · Rust", "02 · Cargo")),
                               BlocAnnonce("Bloc 2 — Concurrence", ("03 · Async",))))
        cours = self.depot.creer(a)
        chapitres = frappe.get_all("Course Chapter", {"course": cours}, ["name", "title"],
                                   order_by="creation asc")
        self.assertEqual([c["title"] for c in chapitres], ["Bloc 1 — Fondations", "Bloc 2 — Concurrence"])
        lecons = frappe.get_all("Course Lesson", {"course": cours}, ["title", "content"],
                                order_by="creation asc")
        self.assertEqual([l["title"] for l in lecons], ["01 · Rust", "02 · Cargo", "03 · Async"])
        self.assertTrue(all(not (l["content"] or "").strip() for l in lecons),
                        "une séance annoncée ne porte aucun contenu")

    def test_le_parcours_annonce_reste_marque_a_venir_malgre_son_programme(self):
        """Un plan publié ne doit pas faire passer le parcours pour ouvert : c'est `upcoming` qui
        tient la porte, et il ne bouge pas parce que la fiche s'est remplie."""
        a = annonce(title="Annoncé toujours à venir",
                    programme=(BlocAnnonce("Bloc 1", ("01 · A",)),))
        cours = self.depot.creer(a)
        self.assertEqual(frappe.db.get_value("LMS Course", cours, "upcoming"), 1)

    def test_aucun_exercice_n_est_cree_pour_un_programme_annonce(self):
        """Un devoir ou un quiz sur un parcours qui n'ouvre pas serait une porte ouverte par erreur."""
        a = annonce(title="Annoncé sans exercice", programme=(BlocAnnonce("Bloc 1", ("01 · A",)),))
        cours = self.depot.creer(a)
        self.assertEqual(frappe.get_all("LMS Assignment", {"course": cours}), [])
        self.assertEqual(frappe.get_all("LMS Quiz", {"course": cours}), [])

    def test_republier_une_annonce_reecrit_son_programme(self):
        a = annonce(title="Annoncé réécrit", programme=(BlocAnnonce("Bloc 1", ("01 · A", "02 · B")),))
        cours = self.depot.creer(a)
        self.depot.remplacer(cours, annonce(title="Annoncé réécrit",
                                            programme=(BlocAnnonce("Bloc unique", ("01 · A",)),)))
        self.assertEqual(frappe.get_all("Course Chapter", {"course": cours}, pluck="title"), ["Bloc unique"])
        self.assertEqual(frappe.get_all("Course Lesson", {"course": cours}, pluck="title"), ["01 · A"])
