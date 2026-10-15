"""Cas d'usage : publier un lot de parcours dans le catalogue, parcours par parcours."""
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from enum import Enum
from typing import Protocol

from openlab_academy.domain.parcours import Parcours


class Statut(str, Enum):
    CREE = "cree"
    MAJ = "maj"
    IGNORE = "ignore"
    ECHEC = "echec"

    def __str__(self) -> str:
        return self.value


class DepotCatalogue(Protocol):
    """Port de persistance du catalogue de cours."""

    def trouver(self, titre: str) -> str | None: ...
    def a_des_inscrits(self, cours_id: str) -> bool: ...
    def creer(self, parcours: Parcours) -> str: ...
    def remplacer(self, cours_id: str, parcours: Parcours) -> None: ...
    def unite_de_travail(self) -> AbstractContextManager: ...


class PublierParcours:
    def __init__(self, depot: DepotCatalogue, journal: Callable[[str], None]):
        self._depot = depot
        self._journal = journal

    def executer(self, lot: Iterable[Parcours]) -> dict[str, Statut]:
        return {p.title: self._publier(p) for p in lot}

    def _publier(self, parcours: Parcours) -> Statut:
        try:
            with self._depot.unite_de_travail():
                cours_id = self._depot.trouver(parcours.title)
                if cours_id is None:
                    self._depot.creer(parcours)
                    return Statut.CREE
                if self._depot.a_des_inscrits(cours_id):
                    self._journal(f"Publication ignorée : « {parcours.title} » a des inscrits")
                    return Statut.IGNORE
                self._depot.remplacer(cours_id, parcours)
                return Statut.MAJ
        except Exception as e:  # un parcours en échec ne bloque pas les suivants
            self._journal(f"Échec de publication de « {parcours.title} » : {e.__class__.__name__}: {e}")
            return Statut.ECHEC
