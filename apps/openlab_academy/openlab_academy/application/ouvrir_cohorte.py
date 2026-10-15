"""Cas d'usage : ouvrir la cohorte pilote d'un parcours (idempotent)."""
import datetime
from collections.abc import Callable
from typing import Protocol

from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.parcours import Parcours
from openlab_academy.domain.reglages import Reglages, Rythme


class DepotCohortes(Protocol):
    def trouver(self, titre: str) -> str | None: ...
    def creer(self, cohorte: Cohorte) -> str: ...


class OuvrirCohorte:
    def __init__(self, depot: DepotCohortes, reglages: Reglages,
                 aujourd_hui: Callable[[], datetime.date] = datetime.date.today):
        self._depot = depot
        self._reglages = reglages
        self._aujourd_hui = aujourd_hui

    def _debut_par_defaut(self) -> datetime.date:
        cible = self._aujourd_hui() + datetime.timedelta(weeks=self._reglages.delai_ouverture_semaines)
        return cible + datetime.timedelta(days=(self._reglages.jour_ouverture - cible.weekday()) % 7)

    def executer(self, parcours: Parcours, debut: datetime.date | None = None,
                 rythme: Rythme | None = None) -> tuple[str, bool]:
        """Renvoie (identifiant, créée ?). Rythme par défaut : le premier des réglages."""
        cohorte = Cohorte.pilote(parcours, debut or self._debut_par_defaut(),
                                 rythme or self._reglages.rythmes[0], self._reglages)
        existante = self._depot.trouver(cohorte.titre)
        if existante:
            return existante, False
        return self._depot.creer(cohorte), True
