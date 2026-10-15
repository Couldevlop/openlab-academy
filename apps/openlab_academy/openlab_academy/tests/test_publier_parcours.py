import contextlib
import unittest

from openlab_academy.application.publier_parcours import PublierParcours, Statut
from openlab_academy.tests.fabriques import parcours


class DepotEnMemoire:
    """Implémentation réelle du port DepotCatalogue, en mémoire, avec transactions."""

    def __init__(self, inscrits=(), echoue_sur=()):
        self.cours: dict[str, object] = {}
        self.inscrits = set(inscrits)
        self.echoue_sur = set(echoue_sur)

    def trouver(self, titre):
        return titre if titre in self.cours else None

    def a_des_inscrits(self, cours_id):
        return cours_id in self.inscrits

    def creer(self, p):
        self._ecrire(p)
        return p.title

    def remplacer(self, cours_id, p):
        self._ecrire(p)

    def _ecrire(self, p):
        self.cours[p.title] = p
        if p.title in self.echoue_sur:
            raise RuntimeError("écriture impossible")

    @contextlib.contextmanager
    def unite_de_travail(self):
        instantane = dict(self.cours)
        try:
            yield
        except Exception:
            self.cours = instantane
            raise


class TestPublierParcours(unittest.TestCase):
    def setUp(self):
        self.journal = []

    def publier(self, depot, *lot):
        return PublierParcours(depot, self.journal.append).executer(lot)

    def test_creation_puis_mise_a_jour(self):
        depot = DepotEnMemoire()
        self.assertEqual(self.publier(depot, parcours()), {"T": Statut.CREE})
        nouveau = parcours(short_introduction="nouvelle")
        self.assertEqual(self.publier(depot, nouveau), {"T": Statut.MAJ})
        self.assertIs(depot.cours["T"], nouveau)

    def test_cours_avec_inscrits_jamais_modifie(self):
        depot = DepotEnMemoire(inscrits={"T"})
        original = parcours()
        depot.cours["T"] = original
        self.assertEqual(self.publier(depot, parcours(short_introduction="x")), {"T": Statut.IGNORE})
        self.assertIs(depot.cours["T"], original)
        self.assertIn("« T » a des inscrits", self.journal[0])

    def test_echec_isole_et_annule(self):
        depot = DepotEnMemoire(echoue_sur={"KO"})
        statuts = self.publier(depot, parcours(title="KO"), parcours(title="OK"))
        self.assertEqual(statuts, {"KO": Statut.ECHEC, "OK": Statut.CREE})
        self.assertNotIn("KO", depot.cours)
        self.assertIn("OK", depot.cours)
        self.assertIn("« KO »", self.journal[0])
        self.assertIn("RuntimeError", self.journal[0])

    def test_statut_serialisable(self):
        self.assertEqual(Statut.CREE.value, "cree")
        self.assertEqual(str(Statut.ECHEC), "echec")
