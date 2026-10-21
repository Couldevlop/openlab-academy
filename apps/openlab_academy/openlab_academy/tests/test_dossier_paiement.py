import unittest
from datetime import date

from openlab_academy.domain.dossier_paiement import Dossier, RappelDu, Statut, bloque, rappels_dus, statut
from openlab_academy.domain.echeancier import Echeance

INSCRIPTION = date(2026, 10, 15)
ECHEANCES = (
    Echeance(INSCRIPTION, 10000, "Frais d'inscription"),
    Echeance(date(2026, 11, 10), 30000, "Tranche 1"),
    Echeance(date(2026, 12, 10), 30000, "Tranche 2"),
)


def dossier(paye=0, **kw):
    return Dossier(echeances=ECHEANCES, paye=paye, frais_inscription=10000, **kw)


class StatutTest(unittest.TestCase):
    def test_frais_non_payes_bloquent_des_l_inscription(self):
        self.assertEqual(statut(dossier(0), INSCRIPTION), Statut.EN_RETARD)
        self.assertTrue(bloque(dossier(0), INSCRIPTION))
        self.assertEqual(statut(dossier(10000), INSCRIPTION), Statut.A_JOUR)
        self.assertFalse(bloque(dossier(10000), INSCRIPTION))

    def test_echeance_du_10_en_retard_le_11(self):
        d = dossier(10000)
        self.assertEqual(statut(d, date(2026, 11, 10)), Statut.A_JOUR)
        self.assertEqual(statut(d, date(2026, 11, 11)), Statut.EN_RETARD)

    def test_paiement_partiel_reste_en_retard(self):
        self.assertEqual(statut(dossier(25000), date(2026, 11, 11)), Statut.EN_RETARD)
        self.assertEqual(statut(dossier(40000), date(2026, 11, 11)), Statut.A_JOUR)

    def test_delai_couvre_jusqu_a_sa_date_incluse(self):
        d = dossier(0, delai_jusqu_au=date(2026, 11, 20))
        self.assertEqual(statut(d, INSCRIPTION), Statut.A_JOUR)
        self.assertEqual(statut(d, date(2026, 11, 20)), Statut.A_JOUR)
        self.assertEqual(statut(d, date(2026, 11, 21)), Statut.EN_RETARD)

    def test_dispense_jamais_bloque(self):
        d = dossier(0, dispense=True)
        self.assertEqual(statut(d, date(2027, 1, 1)), Statut.DISPENSE)
        self.assertFalse(bloque(d, date(2027, 1, 1)))

    def test_solde(self):
        self.assertEqual(statut(dossier(70000), date(2027, 1, 1)), Statut.SOLDE)
        self.assertEqual(statut(dossier(80000), date(2027, 1, 1)), Statut.SOLDE)

    def test_totaux_et_prochaine(self):
        d = dossier(15000)
        self.assertEqual(d.total, 70000)
        self.assertEqual(d.reste, 55000)
        self.assertEqual(dossier(90000).reste, 0)
        self.assertEqual(d.du_echu(date(2026, 11, 11)), 40000)
        self.assertEqual(d.du_echu(INSCRIPTION), 0)
        self.assertEqual(d.prochaine(INSCRIPTION), ECHEANCES[1])
        self.assertEqual(dossier(0).prochaine(INSCRIPTION), ECHEANCES[0])
        self.assertIsNone(dossier(70000).prochaine(INSCRIPTION))


class RappelsTest(unittest.TestCase):
    def test_rappels_7_3_1(self):
        d = dossier(15000)
        r = rappels_dus(d, date(2026, 11, 3))
        self.assertEqual(r, (RappelDu(ECHEANCES[1], 7, 25000),))
        self.assertEqual(rappels_dus(d, date(2026, 11, 7))[0].jours_avant, 3)
        self.assertEqual(rappels_dus(d, date(2026, 11, 9))[0].jours_avant, 1)
        self.assertEqual(rappels_dus(d, date(2026, 11, 8)), ())
        self.assertEqual(rappels_dus(d, date(2026, 11, 10)), ())

    def test_delais_personnalises(self):
        self.assertEqual(len(rappels_dus(dossier(0), date(2026, 11, 8), delais=(2,))), 1)

    def test_pas_de_rappel_pour_une_echeance_couverte(self):
        self.assertEqual(rappels_dus(dossier(40000), date(2026, 11, 3)), ())

    def test_pas_de_rappel_si_dispense(self):
        self.assertEqual(rappels_dus(dossier(0, dispense=True), date(2026, 11, 3)), ())


if __name__ == "__main__":
    unittest.main()
