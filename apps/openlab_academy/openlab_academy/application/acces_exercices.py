"""Cas d'usage : enregistrer l'ouverture d'une leçon, vérifier l'accès à ses exercices."""
import datetime
from collections.abc import Callable
from typing import Protocol

from openlab_academy.domain.reglages import Reglages
from openlab_academy.domain.verrou import verifier_deblocage

Horloge = Callable[[], datetime.datetime]


class DepotOuvertures(Protocol):
    def premiere_ouverture(self, apprenant: str, lecon: str) -> datetime.datetime | None: ...
    def enregistrer(self, apprenant: str, lecon: str, quand: datetime.datetime) -> None: ...


class EnregistrerOuverture:
    def __init__(self, depot: DepotOuvertures, horloge: Horloge):
        self._depot = depot
        self._horloge = horloge

    def executer(self, apprenant: str, lecon: str) -> None:
        if self._depot.premiere_ouverture(apprenant, lecon) is None:
            self._depot.enregistrer(apprenant, lecon, self._horloge())


class DelaiDuParcours(Protocol):
    """Délai de déblocage réglé sur le parcours de la leçon ; None : aucun, le réglage global s'applique."""

    def minutes(self, lecon: str) -> int | None: ...


class VerifierAccesExercices:
    def __init__(self, depot: DepotOuvertures, reglages: Reglages, horloge: Horloge,
                 delais: DelaiDuParcours | None = None):
        self._depot = depot
        self._reglages = reglages
        self._horloge = horloge
        self._delais = delais

    def executer(self, apprenant: str, lecon: str) -> None:
        verifier_deblocage(self._depot.premiere_ouverture(apprenant, lecon), self._horloge(),
                           self._delai(lecon))

    def _delai(self, lecon: str) -> int:
        propre = self._delais.minutes(lecon) if self._delais is not None else None
        return propre if propre is not None else self._reglages.delai_exercices_minutes
