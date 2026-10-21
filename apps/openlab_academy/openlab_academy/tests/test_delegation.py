import unittest
from datetime import datetime, timedelta

from openlab_academy.domain.copie import Copie, Statut
from openlab_academy.domain.delegation import (
    Delegation, DelegationRefusee, FaitsDelegation, correcteur_effectif, peut_corriger, verifier_delegation)
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
        self.assertTrue(deleg(cours="P1").couvre(T0, "C1", "EX1", "P1"))
        self.assertFalse(deleg(cours="P1").couvre(T0, "C1", "EX1", "P2"))
        self.assertFalse(deleg(cours="P1").couvre(T0, "C1", "EX1"))  # cours de la copie inconnu
        self.assertFalse(deleg(fin=None).couvre(T0, "C1", "EX1"))  # sans fin : jamais active

    def test_correcteur_sans_delegation_valide(self):
        ds = [deleg(revoquee=True), deleg(fin=T0 - H), Delegation("autre", "z", T0 - H, T0 + H)]
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX1"), "f")

    def test_specificite(self):
        ds = [deleg("glob"), deleg("cours", cours="P1"), deleg("coh", cohorte="C1"), deleg("exo", exercice="EX1")]
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX1", "P1"), "exo")
        self.assertEqual(correcteur_effectif("f", ds, T0, "C1", "EX2", "P1"), "coh")
        self.assertEqual(correcteur_effectif("f", ds, T0, "C2", "EX2", "P1"), "cours")
        self.assertEqual(correcteur_effectif("f", ds, T0, "C2", "EX2", "P2"), "glob")


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


    def test_delegation_par_cours(self):
        self.assertTrue(peut_corriger("s", self.copie, {"f"}, [deleg(cours="P1")], T0, "P1"))
        self.assertFalse(peut_corriger("s", self.copie, {"f"}, [deleg(cours="P1")], T0, "P2"))


FAITS = FaitsDelegation(delegataire_apprenant=False, delegataire_habilite=True, titulaire_habilite=True,
                        titulaire_en_propre=True, titulaire_delegataire=False)


class TestVerifierDelegation(unittest.TestCase):
    """Règle unique, appliquée par l'écran de la console et par l'API."""

    def refus(self, d=None, creation=True, **faits):
        with self.assertRaises(DelegationRefusee) as e:
            verifier_delegation(d or deleg(), FaitsDelegation(**{**FAITS.__dict__, **faits}), T0, creation)
        return str(e.exception)

    def test_delegation_valide(self):
        verifier_delegation(deleg(cohorte="C1"), FAITS, T0, True)

    def test_a_soi_meme(self):
        self.assertIn("à soi-même", self.refus(Delegation("f", "f", T0, T0 + H)))

    def test_sans_fin_ou_bornes_incoherentes(self):
        self.assertIn("date de fin", self.refus(deleg(fin=None)))
        self.assertIn("suivre son début", self.refus(deleg(debut=T0, fin=T0)))
        self.assertIn("passée", self.refus(deleg(fin=T0 - 0.5 * H)))
        verifier_delegation(deleg(fin=T0 - 0.5 * H), FAITS, T0, creation=False)  # une délégation échue se garde

    def test_delegataire_apprenant_du_perimetre(self):
        self.assertIn("apprenant", self.refus(delegataire_apprenant=True))

    def test_delegataire_sans_habilitation(self):
        self.assertIn("habilitation", self.refus(delegataire_habilite=False))

    def test_titulaire_sans_habilitation(self):
        self.assertIn("titulaire", self.refus(titulaire_habilite=False))

    def test_redelegation_refusee(self):
        self.assertIn("reçue", self.refus(titulaire_en_propre=False, titulaire_delegataire=True))
        verifier_delegation(deleg(), FaitsDelegation(**{**FAITS.__dict__, "titulaire_delegataire": True}), T0, True)


if __name__ == "__main__":
    unittest.main()
