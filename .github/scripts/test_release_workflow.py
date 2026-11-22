# -*- coding: utf-8 -*-
"""L'étiquette de livraison doit désigner l'arbre dont le numéro de version a été lu.

Le piège est invisible à la lecture du fichier seul. `release.yml` extrait `main` explicitement, puis
lit `__version__` dans l'arbre obtenu. Mais il est appelé par `promotion.yml` en `workflow_call`,
depuis un `workflow_run` : le contexte github reste celui de l'appelant, où `GITHUB_SHA` vaut la tête
de `main` *avant* la fusion de promotion. Étiqueter `$GITHUB_SHA` pose donc le numéro neuf sur l'arbre
précédent, silencieusement, et à chaque livraison. C'est arrivé pour v0.1.1 et v0.2.0 : les deux
étiquettes désignent un arbre dont `__init__.py` porte le numéro d'avant.

Le test ne lit pas la version de GitHub : il relit le fichier, et refuse que la cible de l'étiquette
vienne d'ailleurs que du commit extrait.
"""
import pathlib
import re
import unittest

RELEASE = pathlib.Path(__file__).resolve().parents[1] / "workflows" / "release.yml"


class TestLEtiquetteDeLivraison(unittest.TestCase):
    def setUp(self):
        self.texte = RELEASE.read_text(encoding="utf-8")

    def test_la_cible_de_l_etiquette_ne_vient_pas_du_contexte_github(self):
        """`$GITHUB_SHA` ment dès que le workflow est appelé par un autre."""
        creation = [l for l in self.texte.splitlines() if "gh release create" in l]
        self.assertTrue(creation, "la création de la release a disparu de release.yml")
        for ligne in creation:
            with self.subTest(ligne.strip()):
                self.assertNotIn("GITHUB_SHA", ligne)

    def test_la_cible_de_l_etiquette_est_le_commit_extrait(self):
        creation = "\n".join(l for l in self.texte.splitlines() if "gh release create" in l)
        cible = re.search(r"--target\s+\"?\$\{?(\w+)\}?\"?", creation)
        self.assertIsNotNone(cible, "la release doit être étiquetée sur une cible explicite")
        nom = cible.group(1)
        self.assertRegex(self.texte, rf"{nom}=\$\(git rev-parse HEAD\)",
                         "la cible doit être le commit extrait, celui dont la version est lue")

    def test_plus_aucun_commentaire_mis_a_part_n_emploie_le_contexte_github(self):
        """Le réalignement l'annonçait aussi dans son message, où il désignait le mauvais commit.

        Les commentaires gardent le droit de le nommer : c'est là qu'on explique le piège.
        """
        for numero, ligne in enumerate(self.texte.splitlines(), start=1):
            if ligne.lstrip().startswith("#"):
                continue
            with self.subTest(ligne=numero):
                self.assertNotIn("GITHUB_SHA", ligne)
