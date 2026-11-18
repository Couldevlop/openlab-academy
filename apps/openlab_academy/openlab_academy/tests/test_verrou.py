import datetime
import unittest

from openlab_academy.application.acces_exercices import EnregistrerOuverture, VerifierAccesExercices
from openlab_academy.domain.reglages import Reglages
from openlab_academy.domain.verrou import ExercicesVerrouilles, verifier_deblocage

H0 = datetime.datetime(2026, 11, 2, 18, 30)


class TestRegleDeDeblocage(unittest.TestCase):
    def test_ouvert_apres_le_delai(self):
        verifier_deblocage(H0, H0 + datetime.timedelta(minutes=60), 60)

    def test_verrouille_avant_le_delai_avec_temps_restant(self):
        with self.assertRaisesRegex(ExercicesVerrouilles, "encore 15 minutes"):
            verifier_deblocage(H0, H0 + datetime.timedelta(minutes=45), 60)

    def test_derniere_minute_arrondie_au_superieur(self):
        with self.assertRaisesRegex(ExercicesVerrouilles, "encore 1 minute"):
            verifier_deblocage(H0, H0 + datetime.timedelta(minutes=59, seconds=30), 60)

    def test_lecon_jamais_ouverte(self):
        with self.assertRaisesRegex(ExercicesVerrouilles, "ouvrez d'abord la leçon"):
            verifier_deblocage(None, H0, 60)

    def test_delai_nul(self):
        verifier_deblocage(H0, H0, 0)


class DepotOuverturesEnMemoire:
    def __init__(self):
        self.ouvertures = {}

    def premiere_ouverture(self, apprenant, lecon):
        return self.ouvertures.get((apprenant, lecon))

    def enregistrer(self, apprenant, lecon, quand):
        self.ouvertures[(apprenant, lecon)] = quand


class DelaiEnMemoire:
    def __init__(self, delais):
        self.delais = delais

    def minutes(self, lecon):
        return self.delais.get(lecon)


class TestCasDUsage(unittest.TestCase):
    def test_seule_la_premiere_ouverture_compte(self):
        depot, horloge = DepotOuverturesEnMemoire(), [H0]
        enregistrer = EnregistrerOuverture(depot, lambda: horloge[0])
        enregistrer.executer("a@x.ci", "L1")
        horloge[0] = H0 + datetime.timedelta(hours=2)
        enregistrer.executer("a@x.ci", "L1")
        self.assertEqual(depot.ouvertures[("a@x.ci", "L1")], H0)

    def test_verification_selon_les_reglages(self):
        depot = DepotOuverturesEnMemoire()
        depot.enregistrer("a@x.ci", "L1", H0)
        tot = VerifierAccesExercices(depot, Reglages(delai_exercices_minutes=30),
                                     lambda: H0 + datetime.timedelta(minutes=10))
        with self.assertRaisesRegex(ExercicesVerrouilles, "encore 20 minutes"):
            tot.executer("a@x.ci", "L1")
        VerifierAccesExercices(depot, Reglages(delai_exercices_minutes=30),
                               lambda: H0 + datetime.timedelta(minutes=30)).executer("a@x.ci", "L1")

    def test_delai_du_parcours_prefere_au_reglage_global(self):
        depot = DepotOuverturesEnMemoire()
        depot.enregistrer("a@x.ci", "L1", H0)
        verifier = VerifierAccesExercices(depot, Reglages(delai_exercices_minutes=60),
                                          lambda: H0 + datetime.timedelta(minutes=10),
                                          DelaiEnMemoire({"L1": 15}))
        with self.assertRaisesRegex(ExercicesVerrouilles, "encore 5 minutes"):
            verifier.executer("a@x.ci", "L1")

    def test_repli_sur_le_reglage_global_sans_delai_de_parcours(self):
        depot = DepotOuverturesEnMemoire()
        depot.enregistrer("a@x.ci", "L1", H0)
        verifier = VerifierAccesExercices(depot, Reglages(delai_exercices_minutes=30),
                                          lambda: H0 + datetime.timedelta(minutes=20), DelaiEnMemoire({}))
        with self.assertRaisesRegex(ExercicesVerrouilles, "encore 10 minutes"):
            verifier.executer("a@x.ci", "L1")
