"""Cas d'usage : ouvrir la cohorte pilote d'un parcours (idempotent)."""
import datetime
from collections.abc import Callable
from typing import Protocol

from openlab_academy.domain.cohorte import Cohorte
from openlab_academy.domain.parcours import Parcours


class DepotCohortes(Protocol):
    def trouver(self, titre: str) -> str | None: ...
    def creer(self, cohorte: Cohorte) -> str: ...


def _lundi_dans_deux_semaines(jour: datetime.date) -> datetime.date:
    cible = jour + datetime.timedelta(weeks=2)
    return cible + datetime.timedelta(days=(7 - cible.weekday()) % 7)


class OuvrirCohorte:
    def __init__(self, depot: DepotCohortes, aujourd_hui: Callable[[], datetime.date] = datetime.date.today):
        self._depot = depot
        self._aujourd_hui = aujourd_hui

    def executer(self, parcours: Parcours, debut: datetime.date | None = None) -> tuple[str, bool]:
        """Renvoie (identifiant, créée ?)."""
        cohorte = Cohorte.pilote(parcours, debut or _lundi_dans_deux_semaines(self._aujourd_hui()))
        existante = self._depot.trouver(cohorte.titre)
        if existante:
            return existante, False
        return self._depot.creer(cohorte), True
