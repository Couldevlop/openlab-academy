#!/usr/bin/env python3
"""Le decoupage de la suite decide de ce qui est exerce : il ne reste pas sans filet.

Un repartiteur fautif ne se voit pas. Il ne casse rien, il ne ralentit rien : il laisse simplement un
module de cote, et la chaine reste verte sur du code que plus personne n'execute. Ces tests portent donc
d'abord sur ce qui ne doit jamais arriver -- un module perdu, un module compte deux fois -- puis sur le
poids, parce qu'une mesure mal lue ramene le desequilibre que la table est censee corriger.

    python -m unittest discover -s .github/scripts -p "test_*.py"
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import lots_de_tests as L  # noqa: E402  (l'import suit l'ajout du dossier au chemin)

TESTS = pathlib.Path(__file__).resolve().parents[2] / "apps" / "openlab_academy" / "openlab_academy" / "tests"


def _dossier(modules: dict[str, int]) -> pathlib.Path:
    """Un dossier de tests pour l'occasion : {nom du module: nombre de methodes de test}."""
    dossier = pathlib.Path(tempfile.mkdtemp())
    for nom, nombre in modules.items():
        corps = "import unittest\n\n\nclass T(unittest.TestCase):\n"
        corps += "".join(f"    def test_{i}(self):\n        pass\n" for i in range(nombre))
        (dossier / f"{nom}.py").write_text(corps, encoding="utf-8")
    return dossier


class TestRepartition(unittest.TestCase):
    def test_aucun_module_perdu_ni_compte_deux_fois(self):
        """Le defaut qui ne se voit pas : un module hors des lots laisse son code non teste, en vert."""
        trouves = {f"test_{i}": (i, float(i)) for i in range(1, 40)}
        for sur in (1, 2, 3, 5, 7):
            with self.subTest(sur=sur):
                places = [m for lot in L.repartir(trouves, sur) for m in lot]
                self.assertEqual(sorted(places), sorted(trouves))
                self.assertEqual(len(places), len(set(places)))

    def test_repartition_deterministe(self):
        """Deux executions doivent donner les memes lots, sinon un echec n'est pas reproductible."""
        trouves = {f"test_{i}": (1, 1.0) for i in range(20)}
        self.assertEqual(L.repartir(trouves, 3), L.repartir(trouves, 3))

    def test_le_plus_lourd_part_en_premier(self):
        """Sans cela, deux modules lourds finissent dans le meme lot."""
        trouves = {"test_a": (1, 100.0), "test_b": (1, 90.0), "test_c": (1, 1.0)}
        lots = L.repartir(trouves, 2)
        self.assertNotEqual([l for l in lots if "test_a" in l], [l for l in lots if "test_b" in l])

    def test_un_lot_par_coureur_meme_sans_assez_de_modules(self):
        self.assertEqual(L.repartir({"test_a": (1, 1.0)}, 3), [["test_a"], [], []])


class TestPoids(unittest.TestCase):
    def test_le_poids_mesure_passe_avant_l_estimation(self):
        dossier = _dossier({"test_rapide_frappe": 50})
        # l'estimation donnerait 50 x 4 = 200 s ; la mesure dit que ce module ne coute rien
        trouves = L.modules(dossier, connus={"test_rapide_frappe": 2.0})
        self.assertEqual(trouves["test_rapide_frappe"], (50, 2.0 + L.AMORCAGE))

    def test_un_module_jamais_mesure_garde_son_estimation(self):
        """Il n'est surtout pas ecarte : un module sans poids connu doit quand meme etre execute."""
        dossier = _dossier({"test_neuf_frappe": 3})
        trouves = L.modules(dossier, connus={})
        self.assertEqual(trouves["test_neuf_frappe"], (3, 3 * L.ESTIMATION_INTEGRATION + L.AMORCAGE))

    def test_l_amorcage_compte_pour_un_module_sans_aucun_test_lent(self):
        """Un module instantane coute quand meme l'amorcage du site : l'ignorer sous-estime les lots
        nombreux, qui sont precisement ceux qu'on remplit de petits modules."""
        dossier = _dossier({"test_domaine": 4})
        self.assertGreaterEqual(L.modules(dossier, connus={"test_domaine": 0.0})["test_domaine"][1],
                                L.AMORCAGE)


class TestMesure(unittest.TestCase):
    JOURNAL = (
        "2026-11-19T14:01:46Z [openlab_academy.tests.test_annonce] Ran 11 tests in 110.209s\n"
        "2026-11-19T14:03:12Z [openlab_academy.tests.test_blocage_frappe] Ran 46 tests in 84.586s\n"
        "2026-11-19T14:03:13Z [openlab_academy.tests.test_un_seul] Ran 1 test in 0.500s\n"
    )

    def test_les_temps_sont_lus_dans_le_journal(self):
        self.assertEqual(L.mesurer(self.JOURNAL),
                         {"test_annonce": 110.2, "test_blocage_frappe": 84.6, "test_un_seul": 0.5})

    def test_un_module_execute_deux_fois_garde_le_temps_le_plus_long(self):
        """Une reprise de job laisse deux temps pour le meme module : se tromper du cote prudent."""
        double = self.JOURNAL + "x [openlab_academy.tests.test_annonce] Ran 11 tests in 310.000s\n"
        self.assertEqual(L.mesurer(double)["test_annonce"], 310.0)

    def test_un_journal_sans_temps_ne_donne_rien(self):
        self.assertEqual(L.mesurer("rien a voir ici\nRan 3 tests in 1.000s\n"), {})

    def test_la_table_livree_couvre_les_modules_du_depot(self):
        """Une table a jour est la seule chose qui empeche le desequilibre de revenir en silence."""
        connus = L.mesures()
        self.assertTrue(connus, L.TABLE)
        presents = {c.stem for c in TESTS.glob("test_*.py")}
        self.assertEqual(presents - set(connus), set(),
                         "modules sans cout mesure : refaire la table avec --mesurer")

    def test_la_table_est_du_json_trie(self):
        donnees = json.loads(L.TABLE.read_text(encoding="utf-8"))
        self.assertEqual(list(donnees["secondes"]), sorted(donnees["secondes"]))
        self.assertIn("execution", donnees["mesure"])


class TestLotsReels(unittest.TestCase):
    """Sur les modules du depot : c'est la seule mesure qui compte pour le delai du job."""

    def test_les_deux_lots_tiennent_dans_le_delai_avec_de_la_marge(self):
        trouves = L.modules(TESTS)
        charges = [sum(trouves[m][1] for m in lot) for lot in L.repartir(trouves, 2)]
        for i, charge in enumerate(charges, 1):
            with self.subTest(lot=i):
                self.assertLess(charge / 60, 35, f"lot {i} : {charge / 60:.1f} min pour un delai de 50")

    def test_les_lots_sont_equilibres(self):
        trouves = L.modules(TESTS)
        charges = [sum(trouves[m][1] for m in lot) for lot in L.repartir(trouves, 2)]
        ecart = (max(charges) - min(charges)) / max(charges)
        self.assertLess(ecart, 0.15, f"ecart de {ecart:.0%} entre les lots")


if __name__ == "__main__":
    unittest.main()
