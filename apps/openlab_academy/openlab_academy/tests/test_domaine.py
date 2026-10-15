import dataclasses
import unittest

from openlab_academy.domain.parcours import Bloc, Module, Niveau, ParcoursInvalide
from openlab_academy.tests.fabriques import parcours, projet


class TestInvariantsParcours(unittest.TestCase):
    def test_parcours_valide(self):
        self.assertEqual(parcours().title, "T")

    def test_portfolio_doit_compter_10_projets(self):
        with self.assertRaisesRegex(ParcoursInvalide, r"portfolio: 10 projets attendus, 9 trouvés"):
            parcours(portfolio=tuple(projet() for _ in range(9)))

    def test_apres_module_doit_exister(self):
        portfolio = tuple(projet(apres_module="99" if i == 4 else "01") for i in range(10))
        with self.assertRaisesRegex(ParcoursInvalide, r"portfolio\[4\]\.apres_module: module '99' inexistant"):
            parcours(portfolio=portfolio)

    def test_projet_portfolio_sans_module_refuse(self):
        portfolio = tuple(projet(apres_module=None if i == 2 else "01") for i in range(10))
        with self.assertRaisesRegex(ParcoursInvalide, r"portfolio\[2\]\.apres_module manquant"):
            parcours(portfolio=portfolio)

    def test_capstone_ne_se_rattache_pas_a_un_module(self):
        with self.assertRaisesRegex(ParcoursInvalide, r"capstone\.apres_module doit être vide"):
            parcours(capstone=projet(apres_module="01"))

    def test_remuneration_en_keuros_interdite(self):
        for champ in ("title", "short_introduction", "description"):
            with self.subTest(champ=champ), self.assertRaisesRegex(
                    ParcoursInvalide, rf"{champ}: rémunération en k€ interdite"):
                parcours(**{champ: "Rémunération visée : 35–55 k€"})

    def test_numeros_de_module_uniques(self):
        blocs = (Bloc("B1", (Module("01", "M", "c", "l"),)), Bloc("B2", (Module("01", "N", "c", "l"),)))
        with self.assertRaisesRegex(ParcoursInvalide, r"module '01' en double"):
            parcours(blocs=blocs)

    def test_duree_positive(self):
        with self.assertRaisesRegex(ParcoursInvalide, r"duree_h doit être positive"):
            projet(duree_h=0)

    def test_titres_limites_a_120_caracteres(self):
        long = "x" * 121
        for fabrique in (lambda: projet(titre=long),
                         lambda: parcours(blocs=(Bloc(long, (Module("01", "M", "c", "l"),)),)),
                         lambda: parcours(blocs=(Bloc("B", (Module("01", long, "c", "l"),)),))):
            with self.subTest(), self.assertRaisesRegex(ParcoursInvalide, r"titre trop long \(121 > 120\)"):
                fabrique()
        self.assertEqual(projet(titre="x" * 120).titre, "x" * 120)

    def test_entites_immuables(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            parcours().title = "autre"


class TestPlanDesChapitres(unittest.TestCase):
    def test_projets_intercales_apres_leur_module_puis_capstone(self):
        blocs = (Bloc("B1", (Module("01", "Un", "c", "l"),)), Bloc("B2", (Module("02", "Deux", "c", "l"),)))
        portfolio = tuple(projet(titre=f"P{i}", apres_module="02" if i == 10 else "01") for i in range(1, 11))
        chapitres = parcours(blocs=blocs, portfolio=portfolio).chapitres()
        titres = [c.titre for c in chapitres]
        self.assertEqual(titres[0], "B1")
        self.assertEqual(titres[1:10], [f"Projet {i} — P{i}" for i in range(1, 10)])
        self.assertEqual(titres[10:], ["B2", "Projet 10 — P10", "Capstone — Cap"])
        self.assertEqual(chapitres[0].modules[0].title, "Un")
        self.assertIsNone(chapitres[0].projet)
        self.assertEqual(chapitres[-1].projet.titre, "Cap")
        self.assertEqual(chapitres[-1].modules, ())

    def test_libelle_niveau(self):
        self.assertEqual([n.libelle for n in Niveau], ["Guidé", "Semi-guidé", "Autonome"])
