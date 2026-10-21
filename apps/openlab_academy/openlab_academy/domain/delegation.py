"""Domaine : délégation de la correction par un titulaire (formateur, juré) à un autre correcteur, sur une période.

Une seule règle, appliquée par l'écran de la console comme par l'API : on ne délègue ni à soi-même, ni sans date de
fin, ni à un apprenant du périmètre, ni à quelqu'un sans habilitation de correcteur (formateur, jury, responsable)
sur ce périmètre, et l'on ne redélègue pas ce que l'on a soi-même reçu par délégation. Périmètre : cours, cohorte,
exercice (vide : tout ce que le titulaire corrige). L'expiration est automatique : passé la fin, elle ne couvre plus.
"""
from dataclasses import dataclass
from datetime import datetime

from openlab_academy.domain.copie import Copie


class DelegationRefusee(ValueError):
    """La délégation demandée enfreint la règle commune."""


@dataclass(frozen=True)
class Delegation:
    titulaire: str
    delegataire: str
    debut: datetime
    fin: datetime | None
    cohorte: str | None = None
    exercice: str | None = None
    revoquee: bool = False
    cours: str | None = None

    def couvre(self, maintenant: datetime, cohorte: str | None, exercice: str | None,
               cours: str | None = None) -> bool:
        return (not self.revoquee and self.fin is not None and self.debut <= maintenant <= self.fin
                and self.cohorte in (None, cohorte) and self.exercice in (None, exercice)
                and self.cours in (None, cours))

    @property
    def specificite(self) -> int:
        """Exercice > cohorte > cours > tout le périmètre du titulaire."""
        return 4 * (self.exercice is not None) + 2 * (self.cohorte is not None) + (self.cours is not None)


@dataclass(frozen=True)
class FaitsDelegation:
    """Ce que l'adaptateur sait des deux personnes sur le périmètre de la délégation."""

    delegataire_apprenant: bool  # inscrit comme apprenant dans la cohorte ou le cours visés
    delegataire_habilite: bool  # formateur, juré ou responsable sur le périmètre
    titulaire_habilite: bool
    titulaire_en_propre: bool  # formateur ou juré du périmètre par lui-même (pas seulement par un rôle)
    titulaire_delegataire: bool  # délégataire d'une délégation active qui recoupe ce périmètre


def verifier_delegation(d: Delegation, faits: FaitsDelegation, maintenant: datetime, creation: bool) -> None:
    if d.delegataire == d.titulaire:
        raise DelegationRefusee("on ne se délègue pas une correction à soi-même")
    if d.fin is None:
        raise DelegationRefusee("une délégation a toujours une date de fin")
    if d.fin <= d.debut:
        raise DelegationRefusee("la fin de la délégation doit suivre son début")
    if creation and d.fin <= maintenant:
        raise DelegationRefusee("la fin de la délégation est déjà passée")
    if faits.titulaire_delegataire and not faits.titulaire_en_propre:
        raise DelegationRefusee("une correction reçue par délégation ne se délègue pas à nouveau")
    if not faits.titulaire_habilite:
        raise DelegationRefusee("le titulaire n'est pas correcteur sur ce périmètre")
    if faits.delegataire_apprenant:
        raise DelegationRefusee("le délégataire est apprenant sur ce périmètre")
    if not faits.delegataire_habilite:
        raise DelegationRefusee("le délégataire n'a aucune habilitation de correcteur (formateur, jury ou "
                                "responsable) sur ce périmètre")


def correcteur_effectif(titulaire: str, delegations, maintenant: datetime, cohorte: str | None,
                        exercice: str | None, cours: str | None = None) -> str:
    """Délégataire de la délégation active la plus spécifique, sinon le titulaire."""
    actives = [d for d in delegations if d.titulaire == titulaire and d.couvre(maintenant, cohorte, exercice, cours)]
    if not actives:
        return titulaire
    return max(actives, key=lambda d: d.specificite).delegataire


def peut_corriger(acteur: str, copie: Copie, titulaires: set[str], delegations, maintenant: datetime,
                  cours: str | None = None) -> bool:
    """Un apprenant ne corrige jamais sa propre copie, même s'il est formateur par ailleurs."""
    if acteur == copie.apprenant:
        return False
    if acteur in titulaires:
        return True
    return any(d.delegataire == acteur and d.titulaire in titulaires
               and d.couvre(maintenant, copie.cohorte, copie.exercice, cours) for d in delegations)
