import json
import unittest

from openlab_academy.domain.parcours import Module
from openlab_academy.domain.reglages import CritereBareme, Reglages
from openlab_academy.infrastructure import editorjs
from openlab_academy.tests.fabriques import projet


REGLAGES = Reglages()


def blocs(contenu: str) -> list[dict]:
    return json.loads(contenu)["blocks"]


def texte(contenu: str) -> str:
    return json.dumps(blocs(contenu), ensure_ascii=False)


class TestRenduModule(unittest.TestCase):
    def test_structure_et_devoir_embarque(self):
        b = blocs(editorjs.lecon_module(Module("01", "M", "Le contenu", "Le livrable"), "DEV-1", 8))
        self.assertEqual([x["type"] for x in b], ["header", "paragraph", "paragraph", "header", "paragraph", "assignment"])
        self.assertEqual(b[1]["data"]["text"], "Le contenu")
        self.assertEqual(b[-1]["data"], {"assignment": "DEV-1"})

    def test_xss_neutralise(self):
        """OWASP A03 : aucun HTML actif issu des données."""
        rendu = editorjs.lecon_module(Module("01", "M", "<script>alert(1)</script>", '<img onerror="x">'), "D", 8)
        self.assertNotIn("<script>", texte(rendu))
        self.assertNotIn("<img", texte(rendu))
        self.assertIn("&lt;script&gt;", texte(rendu))


class TestRenduProjet(unittest.TestCase):
    def test_enonce_complet(self):
        rendu = texte(editorjs.lecon_projet(projet(exigences_specifiques=("Spécifique",)), "D", REGLAGES))
        for attendu in ("Guidé", "~12 h", "Contexte", "Fonctionnalités attendues", "Critères d'acceptation",
                        "couverture ≥ 70 %", "Spécifique", "Fonctionnel : 40 %", "Documentation : 10 %"):
            self.assertIn(attendu, rendu)
        self.assertEqual(blocs(editorjs.lecon_projet(projet(), "D", REGLAGES))[-1]["data"], {"assignment": "D"})

    def test_xss_neutralise_dans_toutes_les_listes(self):
        p = projet(contexte="<svg onload=x>", objectifs=("<b>o</b>",), stack=("<i>s</i>",),
                   criteres_acceptation=("<a href=javascript:x>",))
        rendu = texte(editorjs.lecon_projet(p, "D", REGLAGES))
        for interdit in ("<svg", "<b>o", "<i>", "<a href"):
            self.assertNotIn(interdit, rendu)

    def test_exigences_et_bareme_lus_dans_les_reglages(self):
        reglages = Reglages(exigences_communes=("Exigence maison",),
                            bareme=(CritereBareme("Démo", 70), CritereBareme("<Code>", 30)))
        rendu = texte(editorjs.lecon_projet(projet(), "D", reglages))
        self.assertIn("Exigence maison", rendu)
        self.assertNotIn("couverture ≥ 70 %", rendu)
        self.assertIn("Démo : 70 %", rendu)
        self.assertIn("&lt;Code&gt; : 30 %", rendu)


class TestDureeModule(unittest.TestCase):
    def test_duree_affichee_selon_les_reglages(self):
        rendu = texte(editorjs.lecon_module(Module("01", "M", "c", "l"), "D", 6))
        self.assertIn("Format : ~6 h", rendu)


class TestConsignes(unittest.TestCase):
    def test_consigne_module(self):
        self.assertIn("Le &lt;livrable&gt;", editorjs.consigne_module(Module("01", "M", "c", "Le <livrable>")))

    def test_consigne_projet_echappee(self):
        c = editorjs.consigne_projet(projet(titre="<x>", criteres_acceptation=("a & b", "<c>")))
        self.assertIn("« &lt;x&gt; »", c)
        self.assertIn("<li>a &amp; b</li><li>&lt;c&gt;</li>", c)
