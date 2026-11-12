"""Domaine des langues : liste blanche stricte, formats régionaux, résolution de la langue d'une requête."""
import unittest

from openlab_academy.domain.langues import DEFAUT, LANGUES, locale, normaliser, resoudre


class TestLangues(unittest.TestCase):
    def test_liste_blanche(self):
        self.assertEqual(LANGUES, ("fr", "en"))
        self.assertEqual(DEFAUT, "fr")
        self.assertEqual(normaliser("en"), "en")
        self.assertEqual(normaliser("fr"), "fr")

    def test_valeurs_refusees(self):
        for valeur in ("EN", "de", "", None, "../en", "en<script>", " en", "en-GB", 1, ["en"]):
            self.assertIsNone(normaliser(valeur), valeur)

    def test_locale(self):
        self.assertEqual(locale("en"), "en-GB")
        self.assertEqual(locale("fr"), "fr-FR")

    def test_resoudre_parametre_valide_prioritaire(self):
        self.assertEqual(resoudre("en", "fr", "fr", True, "fr"), "en")
        self.assertEqual(resoudre("en", None, None, False, "fr"), "en")

    def test_resoudre_visiteur(self):
        self.assertEqual(resoudre(None, "en", None, False, "de"), "en")
        self.assertEqual(resoudre(None, "de", None, False, "en"), "fr")
        self.assertEqual(resoudre("de", None, None, False, "en"), "fr")
        self.assertEqual(resoudre("de", "en", None, False, "fr"), "en")

    def test_resoudre_compte_connecte(self):
        self.assertEqual(resoudre(None, None, "fr", True, "en"), "en")
        self.assertEqual(resoudre(None, None, None, True, "de"), "fr")
        self.assertEqual(resoudre(None, None, "en", True, "de"), "en")
        self.assertEqual(resoudre("de", None, "en", True, "fr"), "en")
        self.assertEqual(resoudre("de", None, None, True, "en"), "fr")
