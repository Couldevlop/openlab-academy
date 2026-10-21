import unittest
from datetime import date

from openlab_academy.domain.echeancier import (
    Echeance, Mode, Tarif, TarifInvalide, dixieme_suivant, echeancier, inscription_permise, replanifier,
)

T = Tarif(50_000, 600_000, 700_000, 800_000)
DEBUT, FIN = date(2026, 11, 2), date(2027, 2, 1)


def lignes(res):
    return [(e.date_limite, e.montant) for e in res]


class TestEcheancier(unittest.TestCase):
    def test_une_fois(self):
        res = echeancier(Mode.UNE_FOIS, T, date(2026, 10, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2026, 10, 15), 50_000), (date(2026, 11, 10), 550_000)])
        self.assertEqual(res[0].libelle, "Frais d'inscription")

    def test_deux_tranches(self):
        res = echeancier(Mode.DEUX_TRANCHES, T, date(2026, 10, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2026, 10, 15), 50_000), (date(2026, 11, 10), 325_000),
                                       (date(2026, 12, 10), 325_000)])

    def test_deux_tranches_mi_parcours_deja_passe(self):
        res = echeancier(Mode.DEUX_TRANCHES, T, date(2026, 12, 20), DEBUT, FIN)
        self.assertEqual([e.date_limite for e in res[1:]], [date(2027, 1, 10), date(2027, 2, 10)])

    def test_mensuel_parts_multiples_de_5(self):
        t = Tarif(50_000, 600_000, 700_000, 800_005)
        res = echeancier(Mode.MENSUEL, t, date(2026, 10, 15), DEBUT, FIN)
        self.assertEqual([e.date_limite for e in res[1:]],
                         [date(2026, 11, 10), date(2026, 12, 10), date(2027, 1, 10), date(2027, 2, 10)])
        self.assertTrue(all(e.montant % 5 == 0 for e in res))
        self.assertEqual(sum(e.montant for e in res), 800_005)
        self.assertEqual([e.montant for e in res[1:4]], [187_500] * 3)
        self.assertEqual(res[-1].montant, 187_505)

    def test_mensuel_cohorte_finie_le_mois_de_l_inscription(self):
        res = echeancier(Mode.MENSUEL, T, date(2026, 10, 15), date(2026, 9, 1), date(2026, 10, 20))
        self.assertEqual(lignes(res), [(date(2026, 10, 15), 50_000), (date(2026, 11, 10), 750_000)])

    def test_inscription_le_10_paie_le_10_du_mois_suivant(self):
        res = echeancier(Mode.UNE_FOIS, T, date(2026, 10, 10), DEBUT, FIN)
        self.assertEqual(res[1].date_limite, date(2026, 11, 10))

    def test_dixieme_suivant_change_d_annee(self):
        self.assertEqual(dixieme_suivant(date(2026, 12, 31)), date(2027, 1, 10))
        self.assertEqual(dixieme_suivant(date(2026, 12, 31), 5), date(2027, 1, 5))


class TestReplanifier(unittest.TestCase):
    def test_mensuel_vers_une_fois(self):
        res = replanifier(Mode.UNE_FOIS, T, 50_000 + 2 * 187_500, date(2026, 12, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2026, 12, 15), 425_000), (date(2027, 1, 10), 175_000)])
        self.assertEqual(res[0].libelle, "Déjà versé")

    def test_deja_solde(self):
        res = replanifier(Mode.UNE_FOIS, T, 700_000, date(2026, 12, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2026, 12, 15), 600_000)])

    def test_exactement_solde(self):
        res = replanifier(Mode.UNE_FOIS, T, 600_000, date(2026, 12, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2026, 12, 15), 600_000)])

    def test_rien_verse_pas_de_ligne_deja_verse(self):
        res = replanifier(Mode.UNE_FOIS, T, 0, date(2026, 12, 15), DEBUT, FIN)
        self.assertEqual(lignes(res), [(date(2027, 1, 10), 600_000)])

    def test_vers_mensuel_repartit_le_reste(self):
        res = replanifier(Mode.MENSUEL, T, 50_000, date(2026, 11, 20), DEBUT, FIN)
        self.assertEqual([e.date_limite for e in res[1:]],
                         [date(2026, 12, 10), date(2027, 1, 10), date(2027, 2, 10)])
        self.assertEqual(sum(e.montant for e in res), 800_000)
        self.assertTrue(all(e.montant % 5 == 0 for e in res))
        self.assertTrue(all(e.date_limite > date(2026, 11, 20) for e in res[1:]))


class TestInscription(unittest.TestCase):
    def test_inscription_permise(self):
        self.assertTrue(inscription_permise(DEBUT, date(2027, 1, 2)))
        self.assertFalse(inscription_permise(DEBUT, date(2027, 1, 3)))

    def test_fin_de_mois_courte(self):
        self.assertTrue(inscription_permise(date(2026, 12, 31), date(2027, 2, 28)))
        self.assertFalse(inscription_permise(date(2026, 12, 31), date(2027, 3, 1)))


class TestTarif(unittest.TestCase):
    def test_valide(self):
        T.valider()
        self.assertEqual(T.prix(Mode.MENSUEL), 800_000)
        self.assertEqual(T.prix(Mode.DEUX_TRANCHES), 700_000)

    def test_invalides(self):
        for t in (Tarif(50_001, 600_000, 700_000, 800_000), Tarif(50_000, 600_000, 700_000, 800_001),
                  Tarif(50_000, 700_000, 600_000, 800_000), Tarif(50_000, 600_000, 600_000, 800_000),
                  Tarif(600_000, 600_000, 700_000, 800_000), Tarif(0, 600_000, 700_000, 800_000),
                  Tarif(50_000, 0, 700_000, 800_000), Tarif(-5, 600_000, 700_000, 800_000)):
            with self.subTest(t=t), self.assertRaises(TarifInvalide):
                t.valider()

    def test_echeance_figee(self):
        e = Echeance(date(2026, 1, 1), 5, "x")
        with self.assertRaises(Exception):
            e.montant = 10


if __name__ == "__main__":
    unittest.main()
