"""Domaine : statut d'un dossier de paiement (retard, délai, dispense) et rappels dus.
Le blocage n'est pas stocké : il se calcule à partir des échéances, du payé et du délai ; aucune dépendance Frappe."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from openlab_academy.domain.echeancier import Echeance


class Statut(StrEnum):
    DISPENSE = "dispense"
    SOLDE = "solde"
    A_JOUR = "a_jour"
    EN_RETARD = "en_retard"


@dataclass(frozen=True)
class Dossier:
    echeances: tuple[Echeance, ...]
    paye: int
    delai_jusqu_au: date | None = None
    dispense: bool = False
    frais_inscription: int = 0

    @property
    def total(self) -> int:
        return sum(e.montant for e in self.echeances)

    @property
    def reste(self) -> int:
        return max(self.total - self.paye, 0)

    def du_echu(self, aujourd_hui: date) -> int:
        return sum(e.montant for e in self.echeances if e.date_limite < aujourd_hui)

    def _non_couvertes(self) -> tuple[tuple[Echeance, int], ...]:
        """Échéances (dans l'ordre des dates) avec leur part non couverte : le payé les couvre dans l'ordre."""
        restant = self.paye
        parts = []
        for e in sorted(self.echeances, key=lambda e: e.date_limite):
            couvert = min(restant, e.montant)
            restant -= couvert
            if e.montant > couvert:
                parts.append((e, e.montant - couvert))
        return tuple(parts)

    def prochaine(self, aujourd_hui: date) -> Echeance | None:
        parts = self._non_couvertes()
        return parts[0][0] if parts else None


def statut(dossier: Dossier, aujourd_hui: date) -> Statut:
    if dossier.dispense:
        return Statut.DISPENSE
    if dossier.reste == 0:
        return Statut.SOLDE
    delai_actif = dossier.delai_jusqu_au is not None and aujourd_hui <= dossier.delai_jusqu_au
    if not delai_actif and (dossier.paye < dossier.frais_inscription or dossier.du_echu(aujourd_hui) > dossier.paye):
        return Statut.EN_RETARD
    return Statut.A_JOUR


def bloque(dossier: Dossier, aujourd_hui: date) -> bool:
    return statut(dossier, aujourd_hui) == Statut.EN_RETARD


@dataclass(frozen=True)
class RappelDu:
    echeance: Echeance
    jours_avant: int
    montant: int


def rappels_dus(dossier: Dossier, aujourd_hui: date, delais: tuple[int, ...] = (7, 3, 1)) -> tuple[RappelDu, ...]:
    if dossier.dispense:
        return ()
    return tuple(
        RappelDu(e, (e.date_limite - aujourd_hui).days, part)
        for e, part in dossier._non_couvertes()
        if (e.date_limite - aujourd_hui).days in delais
    )
