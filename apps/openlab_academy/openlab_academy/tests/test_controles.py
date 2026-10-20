"""Contrôles automatiques d'une copie : longueur minimale, lien de dépôt, dépôt public, fichiers attendus."""
import unittest
from unittest import mock

import requests

from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Copie, Statut
from openlab_academy.domain.grille import Critere, Grille, Niveau
from openlab_academy.domain.reglages_evaluation import ReglagesEvaluation, TypeExercice
from openlab_academy.infrastructure.controles import ControleurDepots, attendus
from openlab_academy.infrastructure.instantane_depot import DepotIndisponible
from openlab_academy.tests.http_simule import SHA, Reponse, github

NIVEAUX = (Niveau("Non", "Non", 0), Niveau("Oui", "Oui", 1))
GRILLE = Grille((Critere("fond", "Fond", "Fond", 100, NIVEAUX),))
COPIE = Copie("C1", "a@x.ci", "EX1", "COH1", TypeExercice.PROJET, 1, Statut.RENDUE)
URL = "https://github.com/aya/livrable"
GET = "requests.get"


def contenu(texte="", url="", commit=""):
    return Contenu(texte, url, commit, "sig", "SUB1")


def grille_projet(*controles):
    return Grille((Critere("qualite", "Qualité", "Qualité", 100, NIVEAUX, controles),))


class TestTexte(unittest.TestCase):
    def test_longueur_minimale_reglee(self):
        controleur = ControleurDepots(ReglagesEvaluation(longueur_min_caracteres=10))
        self.assertEqual(controleur.verifier(COPIE, GRILLE, contenu("  court  ")),
                         ["copie trop courte : 5 caractères pour 10 attendus au minimum"])
        self.assertEqual(controleur.verifier(COPIE, GRILLE, contenu("assez long ici")), [])
        self.assertEqual(ControleurDepots(ReglagesEvaluation(longueur_min_caracteres=0)).verifier(
            COPIE, GRILLE, contenu("")), [])

    def test_defaut_du_domaine(self):
        motifs = ControleurDepots(ReglagesEvaluation()).verifier(COPIE, GRILLE, contenu("x" * 199))
        self.assertEqual(motifs, ["copie trop courte : 199 caractères pour 200 attendus au minimum"])

    def test_piece_jointe_presente(self):
        self.assertEqual(ControleurDepots(ReglagesEvaluation()).verifier(
            COPIE, GRILLE, contenu(url="/private/files/rendu.pdf")), [])


class TestDepot(unittest.TestCase):
    def setUp(self):
        self.controleur = ControleurDepots(ReglagesEvaluation())

    def test_lien_refuse_sans_requete(self):
        for url in ("http://github.com/aya/livrable", "https://127.0.0.1/x/y", "https://169.254.169.254/x/y",
                    "https://github.com.evil.ci/aya/livrable", "github.com/aya/livrable"):
            with self.subTest(url=url), mock.patch(GET) as get:
                (motif,) = self.controleur.verifier(COPIE, GRILLE, contenu(url=url))
                self.assertTrue(motif.startswith("lien de dépôt refusé"))
                get.assert_not_called()

    def test_depot_conforme(self):
        with mock.patch(GET, side_effect=github()) as get:
            self.assertEqual(self.controleur.verifier(COPIE, GRILLE, contenu("instantané", URL, SHA)), [])
        demandes = [a.args[0] for a in get.call_args_list]
        self.assertNotIn("https://api.github.com/repos/aya/livrable/commits/main", demandes)  # commit figé réutilisé

    def test_commit_absent_relu_sur_la_branche_par_defaut(self):
        with mock.patch(GET, side_effect=github()) as get:
            self.assertEqual(self.controleur.verifier(COPIE, GRILLE, contenu("", URL, "")), [])
        self.assertIn("https://api.github.com/repos/aya/livrable/commits/main", [a.args[0] for a in get.call_args_list])

    def test_depot_introuvable_ou_prive(self):
        base = "https://api.github.com/repos/aya/livrable"
        with mock.patch(GET, side_effect=github(routes={base: Reponse(404)})):
            self.assertEqual(self.controleur.verifier(COPIE, GRILLE, contenu(url=URL)), ["dépôt introuvable ou privé"])
        with mock.patch(GET, side_effect=github(prive=True)):
            self.assertEqual(self.controleur.verifier(COPIE, GRILLE, contenu(url=URL)), ["dépôt introuvable ou privé"])

    def test_readme_absent(self):
        with mock.patch(GET, side_effect=github(arbre=["src/app.py", "docs/README.md"])):
            self.assertEqual(self.controleur.verifier(COPIE, GRILLE, contenu(url=URL, commit=SHA)),
                             ["fichier attendu absent : README"])

    def test_fichiers_attendus_deduits_des_controles_de_la_grille(self):
        grille = grille_projet("Tests automatisés, couverture ≥ 70 %", "CI GitHub Actions verte",
                               "Secrets hors du code (.env.example fourni)", "Conteneurisé : démarre en une commande")
        with mock.patch(GET, side_effect=github(arbre=["README.md", "src/app.py"])):
            motifs = self.controleur.verifier(COPIE, grille, contenu(url=URL, commit=SHA))
        self.assertEqual(motifs, ["fichier attendu absent : tests automatisés",
                                  "fichier attendu absent : intégration continue (workflow)",
                                  "fichier attendu absent : .env.example",
                                  "fichier attendu absent : Dockerfile ou fichier compose"])
        arbre = ["README.md", "tests/test_app.py", ".github/workflows/ci.yml", ".env.example", "compose.yaml"]
        with mock.patch(GET, side_effect=github(arbre=arbre)):
            self.assertEqual(self.controleur.verifier(COPIE, grille, contenu(url=URL, commit=SHA)), [])

    def test_attendus_sans_doublon(self):
        grille = Grille((Critere("a", "A", "A", 50, NIVEAUX, ("Tests unitaires",)),
                         Critere("b", "B", "B", 50, NIVEAUX, ("Tests d'intégration", "Commits conventionnels"))))
        self.assertEqual([a.libelle for a in attendus(grille)], ["README", "tests automatisés"])

    def test_jeton_transmis_a_l_api_github(self):
        with mock.patch(GET, side_effect=github()) as get:
            ControleurDepots(ReglagesEvaluation(), jeton="ghp_x").verifier(COPIE, GRILLE, contenu(url=URL, commit=SHA))
        self.assertTrue(all(a.kwargs["headers"]["Authorization"] == "Bearer ghp_x" for a in get.call_args_list))

    def test_reseau_en_panne_leve_indisponible(self):
        with mock.patch(GET, side_effect=requests.Timeout("lent")), self.assertRaises(DepotIndisponible):
            self.controleur.verifier(COPIE, GRILLE, contenu(url=URL))
