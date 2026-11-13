"""Supports visuels d'une leçon : figures, tableaux et extraits de code.

Trois exigences se tiennent ensemble. Le domaine refuse un support mal formé plutôt que de le laisser passer
jusqu'à l'écran. Le rendu produit des blocs que le LMS sait afficher, et rien d'autre. Toute donnée venue d'un
parcours traverse l'échappement, y compris dans une cellule de tableau ou une légende, faute de quoi un
fichier de contenu deviendrait un vecteur d'injection (OWASP A03).
"""
import json
import unittest

from openlab_academy.domain.parcours import Extrait, Figure, Module, Tableau
from openlab_academy.infrastructure import editorjs

FIGURE_URL = "/private/files/boucle-agent.svg"


def blocs(document: str) -> list[dict]:
    return json.loads(document)["blocks"]


def module(**kw) -> Module:
    base = {"num": "01", "title": "M", "contenu": "c", "livrable": "l"}
    return Module(**{**base, **kw})


class TestTableau(unittest.TestCase):
    def test_lignes_de_largeur_constante(self):
        with self.assertRaises(ValueError):
            Tableau("t", ("a", "b"), (("1",),))

    def test_entetes_obligatoires(self):
        with self.assertRaises(ValueError):
            Tableau("t", (), (("1",),))

    def test_au_moins_une_ligne(self):
        with self.assertRaises(ValueError):
            Tableau("t", ("a",), ())

    def test_tableau_valide(self):
        t = Tableau("Comparaison", ("Système", "Décide"), (("Agent", "oui"), ("Workflow", "non")))
        self.assertEqual(t.largeur, 2)


class TestFigure(unittest.TestCase):
    def test_nom_de_fichier_svg_exige(self):
        for nom in ("boucle-agent.png", "../secret.svg", "", "boucle agent.svg"):
            with self.subTest(nom), self.assertRaises(ValueError):
                Figure(nom, "légende")

    def test_legende_obligatoire(self):
        with self.assertRaises(ValueError):
            Figure("boucle-agent.svg", "  ")


class TestExtrait(unittest.TestCase):
    def test_langage_connu(self):
        with self.assertRaises(ValueError):
            Extrait("t", "brainfuck", "x")

    def test_code_non_vide(self):
        with self.assertRaises(ValueError):
            Extrait("t", "python", "   ")


class TestRenduDesSupports(unittest.TestCase):
    def _document(self, **kw):
        return blocs(editorjs.lecon_module(module(**kw), "D", 3, figures_urls={"boucle-agent.svg": FIGURE_URL}))

    def test_figure_rendue_en_bloc_image(self):
        figure = Figure("boucle-agent.svg", "La boucle percevoir, raisonner, agir")
        images = [b for b in self._document(figures=(figure,)) if b["type"] == "image"]
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["data"]["url"], FIGURE_URL)
        self.assertEqual(images[0]["data"]["caption"], "La boucle percevoir, raisonner, agir")

    def test_figure_sans_adresse_connue_refusee(self):
        with self.assertRaises(ValueError):
            editorjs.lecon_module(module(figures=(Figure("absente.svg", "l"),)), "D", 3, figures_urls={})

    def test_tableau_rendu_avec_en_tetes(self):
        t = Tableau("Quatre familles", ("Système", "Décide"), (("Agent", "oui"),))
        tables = [b for b in self._document(tableaux=(t,)) if b["type"] == "table"]
        self.assertEqual(len(tables), 1)
        self.assertTrue(tables[0]["data"]["withHeadings"])
        self.assertEqual(tables[0]["data"]["content"], [["Système", "Décide"], ["Agent", "oui"]])

    def test_extrait_rendu_en_bloc_code(self):
        e = Extrait("Boucle minimale", "python", "for tour in range(5):\n    pass")
        codes = [b for b in self._document(extraits=(e,)) if b["type"] == "codeBox"]
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0]["data"]["language"], "python")
        self.assertIn("for tour in range(5):", codes[0]["data"]["code"])

    def test_ordre_de_lecture(self):
        """La figure ouvre la séance, le tableau tranche, le code montre : le lecteur voit avant de lire."""
        types = [b["type"] for b in self._document(
            figures=(Figure("boucle-agent.svg", "l"),),
            tableaux=(Tableau("t", ("a",), (("1",),)),),
            extraits=(Extrait("t", "python", "x = 1"),))]
        self.assertLess(types.index("image"), types.index("table"))
        self.assertLess(types.index("table"), types.index("codeBox"))


class TestInjectionDansLesSupports(unittest.TestCase):
    HOSTILE = '<img src=x onerror="alert(1)">'

    def _texte(self, **kw):
        return editorjs.lecon_module(module(**kw), "D", 3, figures_urls={"boucle-agent.svg": FIGURE_URL})

    def test_legende_echappee(self):
        rendu = self._texte(figures=(Figure("boucle-agent.svg", self.HOSTILE),))
        self.assertNotIn("<img src=x", rendu)
        self.assertIn("&lt;img", rendu)

    def test_cellules_echappees(self):
        rendu = self._texte(tableaux=(Tableau(self.HOSTILE, (self.HOSTILE,), ((self.HOSTILE,),)),))
        self.assertNotIn("<img src=x", rendu)

    def test_code_echappe(self):
        rendu = self._texte(extraits=(Extrait(self.HOSTILE, "python", self.HOSTILE),))
        self.assertNotIn("<img src=x", rendu)


class TestLectureYamlDesSupports(unittest.TestCase):
    """Le lecteur YAML refuse un support mal formé en nommant la clé fautive : un fichier de contenu se
    corrige à la lecture du message, sans ouvrir le code."""

    def _module(self, supplement: dict):
        from openlab_academy.infrastructure.yaml_source import FormatInvalide, _Lecteur
        from openlab_academy.domain.reglages import Reglages
        lecteur = _Lecteur("test.yaml", Reglages())
        base = {"num": "01", "title": "M", "contenu": "c", "livrable": "l"}
        return lecteur.module({**base, **supplement}, "blocs[0].modules[0]."), FormatInvalide

    def test_figures_lues(self):
        m, _ = self._module({"figures": [{"nom": "boucle-agent.svg", "legende": "La boucle"}]})
        self.assertEqual(m.figures, (Figure("boucle-agent.svg", "La boucle"),))

    def test_tableaux_lus(self):
        m, _ = self._module({"tableaux": [{"titre": "T", "entetes": ["a", "b"], "lignes": [["1", "2"]]}]})
        self.assertEqual(m.tableaux, (Tableau("T", ("a", "b"), (("1", "2"),)),))

    def test_extraits_lus(self):
        m, _ = self._module({"code": [{"titre": "T", "langage": "python", "source": "x = 1"}]})
        self.assertEqual(m.extraits, (Extrait("T", "python", "x = 1"),))

    def test_support_mal_forme_refuse_en_nommant_la_cle(self):
        for cle, valeur in (("figures", [{"nom": "x.png", "legende": "l"}]),
                            ("tableaux", [{"titre": "T", "entetes": ["a"], "lignes": [["1", "2"]]}]),
                            ("code", [{"titre": "T", "langage": "cobol", "source": "x"}]),
                            ("figures", "pas une liste")):
            with self.subTest(cle):
                with self.assertRaises(Exception) as capture:
                    self._module({cle: valeur})
                self.assertIn(cle, str(capture.exception))
