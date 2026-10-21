import unittest
from datetime import datetime, timedelta

from openlab_academy.domain.echeances import Echeance, action_due, prochain_recours
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


class TestProchainRecours(unittest.TestCase):
    def test_suppleants_dans_l_ordre_puis_le_responsable(self):
        suite = [prochain_recours("", ("s1", "s2"), "resp")]
        while suite[-1]:
            suite.append(prochain_recours(suite[-1], ("s1", "s2"), "resp"))
        self.assertEqual(suite, ["s1", "s2", "resp", ""])

    def test_sans_suppleant_responsable(self):
        self.assertEqual(prochain_recours("", (), "resp"), "resp")
        self.assertEqual(prochain_recours("", (), ""), "")

    def test_recours_compte_une_fois(self):
        self.assertEqual(prochain_recours("resp", ("resp",), "resp"), "")

    def test_suppleant_retire_le_responsable_prend_le_relais(self):
        self.assertEqual(prochain_recours("ancien", ("s2",), "resp"), "resp")
        self.assertEqual(prochain_recours("ancien", ("s2",), ""), "")


if __name__ == "__main__":
    unittest.main()
