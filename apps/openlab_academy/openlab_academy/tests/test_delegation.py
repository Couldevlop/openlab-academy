import unittest
from datetime import datetime, timedelta

from openlab_academy.domain.copie import Copie, Statut
from openlab_academy.domain.delegation import Delegation, correcteur_effectif, peut_corriger
from openlab_academy.domain.reglages_evaluation import TypeExercice

T0 = datetime(2026, 11, 2, 9, 0)
H = timedelta(hours=1)


def deleg(delegataire="s", debut=T0 - H, fin=T0 + H, **kw):
    return Delegation("f", delegataire, debut, fin, **kw)


class TestDelegation(unittest.TestCase):
    def test_couvre_dans_la_periode(self):
        self.assertTrue(deleg().couvre(T0, "C1", "EX1"))
        self.assertTrue(deleg().couvre(T0 + H, "C1", "EX1"))

    def test_hors_periode_ou_revoquee(self):
        self.assertFalse(deleg().couvre(T0 + 2 * H, "C1", "EX1"))
        self.assertFalse(deleg().couvre(T0 - 2 * H, "C1", "EX1"))
        self.assertFalse(deleg(revoquee=True).couvre(T0, "C1", "EX1"))

    def test_perimetre(self):
        self.assertTrue(deleg(cohorte="C1").couvre(T0, "C1", "EX1"))
        self.assertFalse(deleg(cohorte="C1").couvre(T0, "C2", "EX1"))
        self.assertFalse(deleg(exercice="EX2").couvre(T0, "C1", "EX1"))

    def test_correcteur_sans_delegation_valide(self):
        ds = [deleg(revoquee=True), deleg(fin=T0 - H), Delegation("autre", "z", T0 - H, T0 + H)]
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX1"), "f")

    def test_specificite(self):
        ds = [deleg("glob"), deleg("coh", cohorte="C1"), deleg("exo", exercice="EX1")]
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX1"), "exo")
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX2"), "coh")
        self.assertEqual(correcteur_effectif("f", ds, T0, "C2", "EX2"), "glob")


class TestPeutCorriger(unittest.TestCase):
    copie = Copie("K", "app", "EX1", "C1", TypeExercice.PROJET, 1, Statut.RENDUE)

    def test_titulaire(self):
        self.assertTrue(peut_corriger("f", self.copie, {"f"}, [], T0))

    def test_inconnu(self):
        self.assertFalse(peut_corriger("x", self.copie, {"f"}, [], T0))

    def test_delegataire_actif(self):
        self.assertTrue(peut_corriger("s", self.copie, {"f"}, [deleg()], T0))

    def test_delegataire_expire_ou_hors_perimetre(self):
        self.assertFalse(peut_corriger("s", self.copie, {"f"}, [deleg(fin=T0 - H)], T0))
        self.assertFalse(peut_corriger("s", self.copie, {"f"}, [deleg(cohorte="C2")], T0))

    def test_delegation_d_un_non_titulaire(self):
        self.assertFalse(peut_corriger("s", self.copie, {"autre"}, [deleg()], T0))

    def test_apprenant_formateur_ne_corrige_pas_sa_copie(self):
        self.assertFalse(peut_corriger("app", self.copie, {"app"}, [], T0))
        self.assertFalse(peut_corriger("app", self.copie, {"f"}, [Delegation("f", "app", T0 - H, T0 + H)], T0))


if __name__ == "__main__":
    unittest.main()
