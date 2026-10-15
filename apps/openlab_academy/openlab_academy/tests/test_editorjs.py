import json
import unittest

from openlab_academy.domain.parcours import Module
from openlab_academy.infrastructure import editorjs
from openlab_academy.tests.fabriques import projet


def blocs(contenu: str) -> list[dict]:
    return json.loads(contenu)["blocks"]


def texte(contenu: str) -> str:
    return json.dumps(blocs(contenu), ensure_ascii=False)


class TestRenduModule(unittest.TestCase):
    def test_structure_et_devoir_embarque(self):
        b = blocs(editorjs.lecon_module(Module("01", "M", "Le contenu", "Le livrable"), "DEV-1"))
        self.assertEqual([x["type"] for x in b], ["header", "paragraph", "paragraph", "header", "paragraph", "assignment"])
        self.assertEqual(b[1]["data"]["text"], "Le contenu")
        self.assertEqual(b[-1]["data"], {"assignment": "DEV-1"})

    def test_xss_neutralise(self):
        """OWASP A03 : aucun HTML actif issu des données."""
        rendu = editorjs.lecon_module(Module("01", "M", "<script>alert(1)</script>", '<img onerror="x">'), "D")
        self.assertNotIn("<script>", texte(rendu))
        self.assertNotIn("<img", texte(rendu))
        self.assertIn("&lt;script&gt;", texte(rendu))


class TestRenduProjet(unittest.TestCase):
    def test_enonce_complet(self):
        rendu = texte(editorjs.lecon_projet(projet(exigences_specifiques=("Spécifique",)), "D"))
        for attendu in ("Guidé", "~12 h", "Contexte", "Fonctionnalités attendues", "Critères d'acceptation",
                        "couverture ≥ 70 %", "Spécifique", "Fonctionnel : 40 %", "Documentation : 10 %"):
            self.assertIn(attendu, rendu)
        self.assertEqual(blocs(editorjs.lecon_projet(projet(), "D"))[-1]["data"], {"assignment": "D"})

    def test_xss_neutralise_dans_toutes_les_listes(self):
        p = projet(contexte="<svg onload=x>", objectifs=("<b>o</b>",), stack=("<i>s</i>",),
                   criteres_acceptation=("<a href=javascript:x>",))
        rendu = texte(editorjs.lecon_projet(p, "D"))
        for interdit in ("<svg", "<b>o", "<i>", "<a href"):
            self.assertNotIn(interdit, rendu)

    def test_bareme_totalise_100(self):
        self.assertEqual(sum(poids for _, poids in editorjs.GRILLE), 100)


class TestConsignes(unittest.TestCase):
    def test_consigne_module(self):
        self.assertIn("Le &lt;livrable&gt;", editorjs.consigne_module(Module("01", "M", "c", "Le <livrable>")))

    def test_consigne_projet_echappee(self):
        c = editorjs.consigne_projet(projet(titre="<x>", criteres_acceptation=("a & b", "<c>")))
        self.assertIn("« &lt;x&gt; »", c)
        self.assertIn("<li>a &amp; b</li><li>&lt;c&gt;</li>", c)
