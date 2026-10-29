"""Cas d'usage : un parcours est-il refusé (fermé ou caché) à un apprenant ou à un visiteur ?"""
import datetime
from collections.abc import Callable
from enum import Enum
from typing import Protocol
from urllib.parse import quote

from openlab_academy.domain.fenetre import Fenetre
from openlab_academy.domain.lancement import PhaseLancement

PREFIXE_FERME = "/parcours-ferme/"
CATALOGUE = "/lms/courses"


class Refus(str, Enum):
    FERME = "ferme"
    CACHE = "cache"


class SourceVisibilite(Protocol):
    def phase(self) -> PhaseLancement: ...
    def limite(self, cours: str) -> bool: ...
    def fenetre(self, cours: str) -> Fenetre | None: ...
    def tous_les_cours(self) -> tuple[str, ...]: ...
    def cours_limites_publies(self) -> tuple[str, ...]: ...


class Visibilite:
    def __init__(self, source: SourceVisibilite, aujourd_hui: Callable[[], datetime.date]):
        self._source = source
        self._aujourd_hui = aujourd_hui

    def refus(self, cours: str, agent: bool) -> Refus | None:
        """Les agents ne sont jamais refusés ; le masquage prime sur la fermeture."""
        if agent:
            return None
        if self._source.phase().cache(cours):
            return Refus.CACHE
        if self._source.limite(cours):
            fenetre = self._source.fenetre(cours)
            if fenetre is None or not fenetre.ouverte(self._aujourd_hui()):
                return Refus.FERME
        return None

    def refuses(self, agent: bool) -> frozenset[str]:
        return frozenset(c for c in self._source.tous_les_cours() if self.refus(c, agent) is not None)

    def echus(self) -> tuple[str, ...]:
        """Parcours limités publiés dont la fenêtre est terminée."""
        jour = self._aujourd_hui()
        return tuple(c for c in self._source.cours_limites_publies()
                     if (f := self._source.fenetre(c)) is not None and f.terminee(jour))


def redirection(refus: Refus, cours: str) -> str:
    """Destination d'un refus ; le nom du parcours est encodé en un seul segment."""
    if refus is Refus.FERME:
        return PREFIXE_FERME + quote(cours, safe="")
    return CATALOGUE
