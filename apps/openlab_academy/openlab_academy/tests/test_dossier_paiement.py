import unittest
from datetime import date

from openlab_academy.domain.dossier_paiement import (
    Dossier, RappelDu, Statut, a_echoir, arriere, bloque, exigible, rappels_dus, reste_du, statut)
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

    def test_part_due_de_la_prochaine_echeance(self):
        self.assertEqual(dossier(0).part_prochaine(), 10000)
        self.assertEqual(dossier(15000).part_prochaine(), 25000)
        self.assertEqual(dossier(70000).part_prochaine(), 0)


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


class TableauxTest(unittest.TestCase):
    """Grandeurs des tableaux de bord, cohérentes avec le statut."""

    def test_couverture_dans_l_ordre_des_dates(self):
        self.assertEqual(dossier(40000).couverture(), ((ECHEANCES[0], True), (ECHEANCES[1], True),
                                                       (ECHEANCES[2], False)))
        self.assertEqual([c for _, c in dossier(39995).couverture()], [True, False, False])
        self.assertEqual([c for _, c in dossier(0).couverture()], [False, False, False])

    def test_exigible_frais_puis_echeances_echues_plafonne_au_total(self):
        self.assertEqual(exigible(dossier(0), INSCRIPTION), 10000)
        self.assertEqual(exigible(dossier(0), date(2026, 11, 11)), 40000)
        self.assertEqual(exigible(dossier(0), date(2027, 1, 1)), 70000)
        court = Dossier((Echeance(INSCRIPTION, 5000, "Frais"),), 0, frais_inscription=10000)
        self.assertEqual(exigible(court, INSCRIPTION), 5000)
        self.assertEqual(exigible(dossier(0, dispense=True), date(2027, 1, 1)), 0)

    def test_arriere(self):
        self.assertEqual(arriere(dossier(0), INSCRIPTION), 10000)
        self.assertEqual(arriere(dossier(25000), date(2026, 11, 11)), 15000)
        self.assertEqual(arriere(dossier(40000), date(2026, 11, 11)), 0)
        self.assertEqual(arriere(dossier(90000), date(2027, 1, 1)), 0)
        self.assertEqual(arriere(dossier(0, dispense=True), date(2027, 1, 1)), 0)
        # le délai ne fait pas disparaître l'arriéré : il lève seulement le blocage
        self.assertEqual(arriere(dossier(0, delai_jusqu_au=date(2026, 12, 1)), date(2026, 11, 11)), 40000)

    def test_arriere_coherent_avec_le_statut(self):
        for paye in (0, 5000, 10000, 25000, 40000, 55000, 70000, 80000):
            for jour in (INSCRIPTION, date(2026, 11, 10), date(2026, 11, 11), date(2026, 12, 11), date(2027, 1, 1)):
                for delai in (None, date(2026, 11, 30)):
                    d = dossier(paye, delai_jusqu_au=delai)
                    with self.subTest(paye=paye, jour=jour, delai=delai):
                        if bloque(d, jour):
                            self.assertGreater(arriere(d, jour), 0)
                        if arriere(d, jour) > 0 and statut(d, jour) is not Statut.EN_RETARD:
                            self.assertIsNotNone(delai)
                            self.assertLessEqual(jour, delai)

    def test_a_echoir_parts_non_couvertes_dans_la_fenetre(self):
        self.assertEqual(a_echoir(dossier(15000), date(2026, 11, 1)), 25000)
        self.assertEqual(a_echoir(dossier(0), INSCRIPTION), 40000)  # frais du jour (pas encore échus) + 10/11
        self.assertEqual(a_echoir(dossier(0), date(2026, 11, 11)), 30000)
        self.assertEqual(a_echoir(dossier(15000), date(2026, 10, 1), jours=9), 0)
        self.assertEqual(a_echoir(dossier(0, dispense=True), INSCRIPTION), 0)

    def test_reste_du_nul_si_dispense(self):
        self.assertEqual(reste_du(dossier(15000)), 55000)
        self.assertEqual(reste_du(dossier(0, dispense=True)), 0)


if __name__ == "__main__":
    unittest.main()
