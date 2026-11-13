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


class TestFiguresLivrees(unittest.TestCase):
    """Une figure citée par un parcours doit exister dans les ressources de l'application, sinon la leçon
    s'affiche avec une image morte. Le fichier est produit par docs/Ressources/construire_schemas.py ; la CI
    vérifie en plus que le fichier versionné est bien celui que le script rend."""

    def test_toute_figure_citee_est_livree(self):
        import pathlib

        from openlab_academy.domain.parcours import Parcours
        from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

        ressources = pathlib.Path(__file__).parents[1] / "data" / "ressources"
        manquantes = []
        for parcours in (p for p in charger_dossier(PARCOURS_DIR) if isinstance(p, Parcours)):
            for bloc in parcours.blocs:
                for m in bloc.modules:
                    manquantes += [f"{parcours.title} / {m.num} : {f.nom}"
                                   for f in m.toutes_les_figures if not (ressources / f.nom).is_file()]
        self.assertEqual(manquantes, [], "\n".join(manquantes))


class TestSectionsDeCours(unittest.TestCase):
    """Une leçon est un chapitre, pas un résumé : elle se découpe en sections titrées, chacune pouvant
    porter la figure, le tableau ou l'extrait qui l'illustre, au plus près du texte qui l'explique."""

    def _section(self, **kw):
        from openlab_academy.domain.parcours import Section
        base = {"titre": "La boucle", "paragraphes": ("Un agent décide, agit, observe.",)}
        return Section(**{**base, **kw})

    def test_titre_et_paragraphes_obligatoires(self):
        for invalide in ({"titre": "  "}, {"paragraphes": ()}):
            with self.subTest(invalide), self.assertRaises(ValueError):
                self._section(**invalide)

    def test_sections_rendues_sous_le_contenu(self):
        from openlab_academy.domain.parcours import Section
        sections = (self._section(),
                    Section("Les composants", ("Le modèle, les outils, la mémoire, le contrôle.",
                                               "Sans contrôle, la boucle ne s'arrête pas.")))
        rendu = blocs(editorjs.lecon_module(module(cours=sections), "D", 3))
        titres = [b["data"]["text"] for b in rendu if b["type"] == "header"]
        self.assertIn("La boucle", titres)
        self.assertIn("Les composants", titres)
        textes = [b["data"].get("text", "") for b in rendu if b["type"] == "paragraph"]
        self.assertIn("Sans contrôle, la boucle ne s&#x27;arrête pas.", textes)

    def test_section_porte_ses_propres_supports(self):
        section = self._section(figures=(Figure("boucle-agent.svg", "La boucle"),),
                                tableaux=(Tableau("T", ("a",), (("1",),)),),
                                extraits=(Extrait("E", "python", "x = 1"),))
        rendu = blocs(editorjs.lecon_module(module(cours=(section,)), "D", 3,
                                            figures_urls={"boucle-agent.svg": FIGURE_URL}))
        types = [b["type"] for b in rendu]
        self.assertLess(types.index("header"), types.index("image"))
        for attendu in ("image", "table", "codeBox"):
            self.assertIn(attendu, types)

    def test_texte_des_sections_echappe(self):
        rendu = editorjs.lecon_module(module(cours=(self._section(
            titre='<img src=x onerror="a">', paragraphes=('<img src=x onerror="a">',)),)), "D", 3)
        self.assertNotIn("<img src=x", rendu)


class TestLectureYamlDesSections(unittest.TestCase):
    def _module(self, supplement: dict):
        from openlab_academy.domain.reglages import Reglages
        from openlab_academy.infrastructure.yaml_source import _Lecteur
        base = {"num": "01", "title": "M", "contenu": "c", "livrable": "l"}
        return _Lecteur("test.yaml", Reglages()).module({**base, **supplement}, "blocs[0].modules[0].")

    def test_sections_lues_avec_leurs_supports(self):
        m = self._module({"cours": [
            {"titre": "La boucle", "texte": "Un agent décide.\n\nPuis il agit.",
             "figures": [{"nom": "boucle-agent.svg", "legende": "La boucle"}],
             "tableaux": [{"titre": "T", "entetes": ["a"], "lignes": [["1"]]}],
             "code": [{"titre": "E", "langage": "python", "source": "x = 1"}]}]})
        self.assertEqual(len(m.cours), 1)
        section = m.cours[0]
        self.assertEqual(section.titre, "La boucle")
        self.assertEqual(section.paragraphes, ("Un agent décide.", "Puis il agit."))
        self.assertEqual(section.figures[0].nom, "boucle-agent.svg")
        self.assertEqual(section.tableaux[0].titre, "T")
        self.assertEqual(section.extraits[0].langage, "python")

    def test_section_mal_formee_refusee_en_nommant_la_cle(self):
        with self.assertRaises(Exception) as capture:
            self._module({"cours": [{"titre": "", "texte": "x"}]})
        self.assertIn("cours", str(capture.exception))


class TestLectureYamlDuGuideDeProjet(unittest.TestCase):
    """Le projet final se prépare comme une séance : son guide se lit en sections titrées, avec supports."""

    def _projet(self, supplement: dict):
        from openlab_academy.domain.reglages import Reglages
        from openlab_academy.infrastructure.yaml_source import _Lecteur
        base = {"titre": "Cap", "duree_h": 3, "niveau": "autonome", "contexte": "c", "objectifs": ["o"],
                "fonctionnalites": ["f"], "stack": ["s"], "criteres_acceptation": ["a"],
                "exigences_specifiques": ["e"], "livrables": ["l"]}
        return _Lecteur("test.yaml", Reglages()).projet({**base, **supplement}, "capstone.", False)

    def test_guide_lu_avec_ses_supports(self):
        p = self._projet({
            "figures": [{"nom": "boucle-agent.svg", "legende": "La boucle"}],
            "cours": [{"titre": "Cadrer", "texte": "Écrire la mission.\n\nPuis les limites.",
                       "tableaux": [{"titre": "T", "entetes": ["a"], "lignes": [["1"]]}],
                       "code": [{"titre": "E", "langage": "yaml", "source": "mission: x"}]}]})
        self.assertEqual([s.titre for s in p.cours], ["Cadrer"])
        self.assertEqual(p.cours[0].paragraphes, ("Écrire la mission.", "Puis les limites."))
        self.assertEqual(p.cours[0].tableaux[0].titre, "T")
        self.assertEqual(p.cours[0].extraits[0].langage, "yaml")
        self.assertEqual([f.nom for f in p.toutes_les_figures], ["boucle-agent.svg"])

    def test_section_mal_formee_refusee_en_nommant_la_cle(self):
        with self.assertRaises(Exception) as capture:
            self._projet({"cours": [{"titre": "", "texte": "x"}]})
        self.assertIn("capstone.cours", str(capture.exception))
