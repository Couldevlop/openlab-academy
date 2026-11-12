import unittest
from datetime import date

from openlab_academy.application.visibilite import CATALOGUE, Refus, Visibilite, redirection
from openlab_academy.domain.fenetre import Fenetre
from openlab_academy.domain.lancement import PhaseLancement

JOUR = date(2026, 11, 10)
OUVERTE = Fenetre(date(2026, 11, 2), date(2026, 12, 2))


class SourceFactice:
    def __init__(self, phase=None, limites=None, fenetres=None, publies=None, cours=()):
        self._phase = phase or PhaseLancement(active=False)
        self._limites = set(limites or ())
        self._fenetres = fenetres or {}
        self._publies = tuple(publies or ())
        self._cours = tuple(cours)

    def phase(self):
        return self._phase

    def limite(self, cours):
        return cours in self._limites

    def fenetre(self, cours):
        return self._fenetres.get(cours)

    def tous_les_cours(self):
        return self._cours

    def cours_limites_publies(self):
        return self._publies


def visibilite(source, jour=JOUR):
    return Visibilite(source, lambda: jour)


class TestRefus(unittest.TestCase):
    def test_agent_jamais_refuse(self):
        v = visibilite(SourceFactice(phase=PhaseLancement(), limites={"a"}))
        self.assertIsNone(v.refus("a", agent=True))
        self.assertIsNone(v.refus("b", agent=True))

    def test_cache_pendant_le_lancement(self):
        v = visibilite(SourceFactice(phase=PhaseLancement(visibles=frozenset({"v"}))))
        self.assertEqual(v.refus("b", agent=False), Refus.CACHE)
        self.assertIsNone(v.refus("v", agent=False))

    def test_phase_inactive_rien_de_cache(self):
        v = visibilite(SourceFactice(phase=PhaseLancement(active=False)))
        self.assertIsNone(v.refus("b", agent=False))

    def test_cache_prime_sur_ferme(self):
        v = visibilite(SourceFactice(phase=PhaseLancement(), limites={"a"}))
        self.assertEqual(v.refus("a", agent=False), Refus.CACHE)

    def test_limite_hors_fenetre_ferme(self):
        s = SourceFactice(limites={"a"}, fenetres={"a": OUVERTE})
        self.assertIsNone(visibilite(s).refus("a", agent=False))
        self.assertEqual(visibilite(s, date(2026, 11, 1)).refus("a", agent=False), Refus.FERME)
        self.assertEqual(visibilite(s, date(2026, 12, 3)).refus("a", agent=False), Refus.FERME)

    def test_limite_sans_cohorte_ferme(self):
        v = visibilite(SourceFactice(limites={"a"}))
        self.assertEqual(v.refus("a", agent=False), Refus.FERME)

    def test_non_limite_jamais_ferme(self):
        v = visibilite(SourceFactice(fenetres={"b": OUVERTE}), date(2027, 1, 1))
        self.assertIsNone(v.refus("b", agent=False))


class TestListes(unittest.TestCase):
    def test_refuses_union_caches_et_fermes(self):
        s = SourceFactice(phase=PhaseLancement(visibles=frozenset({"l"})), limites={"l", "f"},
                          fenetres={"l": OUVERTE}, cours=("l", "f", "c"))
        v = visibilite(s)
        self.assertEqual(v.refuses(agent=False), frozenset({"f", "c"}))
        self.assertEqual(v.refuses(agent=True), frozenset())

    def test_refuses_ferme_hors_lancement(self):
        s = SourceFactice(limites={"f"}, fenetres={"f": OUVERTE}, cours=("f", "o"))
        self.assertEqual(visibilite(s, date(2026, 12, 3)).refuses(agent=False), frozenset({"f"}))

    def test_echus(self):
        s = SourceFactice(publies=("fini", "ouvert", "futur", "sans"),
                          fenetres={"fini": Fenetre(date(2026, 9, 1), date(2026, 10, 1)),
                                    "ouvert": OUVERTE,
                                    "futur": Fenetre(date(2026, 12, 1), date(2027, 1, 1))})
        self.assertEqual(visibilite(s).echus(), ("fini",))


class TestRedirection(unittest.TestCase):
    def test_redirection_encodee(self):
        self.assertEqual(redirection(Refus.FERME, "../a b?x=1#y"), "/parcours-ferme/..%2Fa%20b%3Fx%3D1%23y")
        self.assertEqual(redirection(Refus.FERME, "//evil.example"), "/parcours-ferme/%2F%2Fevil.example")
        self.assertEqual(redirection(Refus.CACHE, "x"), CATALOGUE)
        self.assertEqual(CATALOGUE, "/lms/courses")
