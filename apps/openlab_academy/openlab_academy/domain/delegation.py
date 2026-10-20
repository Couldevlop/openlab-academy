"""Domaine : délégation de la correction par un titulaire (formateur) à un suppléant, sur une période."""
from dataclasses import dataclass
from datetime import datetime

from openlab_academy.domain.copie import Copie


@dataclass(frozen=True)
class Delegation:
    titulaire: str
    delegataire: str
    debut: datetime
    fin: datetime
    cohorte: str | None = None
    exercice: str | None = None
    revoquee: bool = False

    def couvre(self, maintenant: datetime, cohorte: str | None, exercice: str | None) -> bool:
        return (not self.revoquee and self.debut <= maintenant <= self.fin
                and self.cohorte in (None, cohorte) and self.exercice in (None, exercice))

    @property
    def specificite(self) -> int:
        return 2 * (self.exercice is not None) + (self.cohorte is not None)


def correcteur_effectif(titulaire: str, delegations, maintenant: datetime, cohorte: str | None,
                        exercice: str | None) -> str:
    """Délégataire de la délégation active la plus spécifique (exercice > cohorte > globale), sinon le titulaire."""
    actives = [d for d in delegations if d.titulaire == titulaire and d.couvre(maintenant, cohorte, exercice)]
    if not actives:
        return titulaire
    return max(actives, key=lambda d: d.specificite).delegataire


def peut_corriger(acteur: str, copie: Copie, titulaires: set[str], delegations, maintenant: datetime) -> bool:
    """Un apprenant ne corrige jamais sa propre copie, même s'il est formateur par ailleurs."""
    if acteur == copie.apprenant:
        return False
    if acteur in titulaires:
        return True
    return any(d.delegataire == acteur and d.titulaire in titulaires
               and d.couvre(maintenant, copie.cohorte, copie.exercice) for d in delegations)
