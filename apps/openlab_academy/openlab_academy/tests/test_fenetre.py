import unittest
from datetime import date, timedelta

from openlab_academy.domain.fenetre import Fenetre, FenetreInvalide, date_ouverture, un_mois_apres


class TestUnMoisApres(unittest.TestCase):
    def test_cas_courants(self):
        self.assertEqual(un_mois_apres(date(2026, 11, 2)), date(2026, 12, 2))
        self.assertEqual(un_mois_apres(date(2026, 12, 15)), date(2027, 1, 15))

    def test_jour_ramene_au_dernier_du_mois(self):
        self.assertEqual(un_mois_apres(date(2027, 1, 31)), date(2027, 2, 28))
        self.assertEqual(un_mois_apres(date(2028, 1, 31)), date(2028, 2, 29))


class TestFenetre(unittest.TestCase):
    F = Fenetre(date(2026, 11, 2), date(2026, 12, 2))

    def test_bornes(self):
        self.assertFalse(self.F.ouverte(date(2026, 11, 1)))
        self.assertTrue(self.F.ouverte(date(2026, 11, 2)))
        self.assertTrue(self.F.ouverte(date(2026, 12, 2)))
        self.assertFalse(self.F.ouverte(date(2026, 12, 3)))

    def test_terminee(self):
        self.assertFalse(self.F.terminee(date(2026, 11, 1)))
        self.assertFalse(self.F.terminee(date(2026, 12, 2)))
        self.assertTrue(self.F.terminee(date(2026, 12, 3)))

    def test_fin_avant_debut_invalide(self):
        with self.assertRaises(FenetreInvalide):
            Fenetre(date(2026, 12, 2), date(2026, 11, 2))


class TestDateOuverture(unittest.TestCase):
    J = date(2026, 11, 2)

    def test_vide_ou_passee_vaut_aujourd_hui(self):
        self.assertEqual(date_ouverture(None, self.J), self.J)
        self.assertEqual(date_ouverture(self.J - timedelta(days=1), self.J), self.J)

    def test_future_conservee(self):
        self.assertEqual(date_ouverture(self.J + timedelta(days=10), self.J), self.J + timedelta(days=10))
