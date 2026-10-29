"""Domaine : phase de lancement, pendant laquelle seuls certains parcours sont visibles."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseLancement:
    active: bool = True
    visibles: frozenset[str] = frozenset()

    def cache(self, cours: str) -> bool:
        return self.active and cours not in self.visibles
