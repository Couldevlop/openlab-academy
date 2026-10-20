import unittest
from datetime import datetime, timedelta

from openlab_academy.domain.echeances import Echeance, action_due, escalade
from openlab_academy.domain.reglages_evaluation import Etape, Expiration, chaines_defaut, TypeExercice

T0 = datetime(2026, 11, 2, 9, 0)
CHAINE = chaines_defaut()[TypeExercice.PROJET]


class TestActionDue(unittest.TestCase):
    def test_rien_avant_le_delai(self):
        e = Echeance(Etape.PAIRS, T0)
        self.assertIsNone(action_due(e, CHAINE, T0 + timedelta(hours=71, minutes=59)))

    def test_action_reglee_apres_le_delai(self):
        e = Echeance(Etape.PAIRS, T0)
        self.assertEqual(action_due(e, CHAINE, T0 + timedelta(hours=72)), Expiration.REATTRIBUER)
        e = Echeance(Etape.FORMATEUR, T0)
        self.assertEqual(action_due(e, CHAINE, T0 + timedelta(hours=100)), Expiration.ESCALADER)


class TestEscalade(unittest.TestCase):
    def test_suppleant(self):
        self.assertEqual(escalade(Etape.FORMATEUR, "sup", "resp"), "sup")

    def test_sans_suppleant_responsable(self):
        self.assertEqual(escalade(Etape.FORMATEUR, None, "resp"), "resp")
        self.assertEqual(escalade(Etape.JURY, "", "resp"), "resp")


if __name__ == "__main__":
    unittest.main()
