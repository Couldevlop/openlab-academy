"""Domaine : statut d'un dossier de paiement (retard, délai, dispense) et rappels dus.
Le blocage n'est pas stocké : il se calcule à partir des échéances, du payé et du délai ; aucune dépendance Frappe."""
from dataclasses import dataclass
from datetime import date, timedelta
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

    def couverture(self) -> tuple[tuple[Echeance, bool], ...]:
        """Échéances dans l'ordre des dates, chacune avec vrai si le payé la couvre entièrement."""
        restant, lignes = self.paye, []
        for e in sorted(self.echeances, key=lambda e: e.date_limite):
            lignes.append((e, restant >= e.montant))
            restant -= min(restant, e.montant)
        return tuple(lignes)

    def prochaine(self, aujourd_hui: date) -> Echeance | None:
        parts = self._non_couvertes()
        return parts[0][0] if parts else None

    def part_prochaine(self) -> int:
        """Part non couverte de la prochaine échéance (0 si tout est couvert)."""
        parts = self._non_couvertes()
        return parts[0][1] if parts else 0


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


def exigible(dossier: Dossier, aujourd_hui: date) -> int:
    """Montant exigible à ce jour : les frais d'inscription et les échéances échues, plafonné au total."""
    if dossier.dispense:
        return 0
    return min(max(dossier.du_echu(aujourd_hui), dossier.frais_inscription), dossier.total)


def en_souffrance(dossier: Dossier, aujourd_hui: date) -> bool:
    """Vrai si une échéance dont la date est passée (strictement) n'est pas couverte. Les frais du jour de
    l'inscription, déjà exigibles, n'y sont pas encore ; un délai ne change rien, une dispense si."""
    return not dossier.dispense and dossier.paye < dossier.du_echu(aujourd_hui)


def arriere(dossier: Dossier, aujourd_hui: date) -> int:
    """Exigible non payé. Un délai ne l'efface pas (il lève seulement le blocage) : tout dossier bloqué a un
    arriéré, et un arriéré sans blocage suppose un délai en cours."""
    return max(exigible(dossier, aujourd_hui) - dossier.paye, 0)


def a_echoir(dossier: Dossier, aujourd_hui: date, jours: int = 30) -> int:
    """Montant qui deviendra exigible d'ici `jours` jours (inclus), hors exigible d'aujourd'hui : les frais du jour de
    l'inscription comptent dans l'arriéré, jamais deux fois. Le payé couvre d'abord l'exigible, puis l'à-échoir ;
    arriéré + à-échoir ne dépasse jamais le reste."""
    if dossier.dispense:
        return 0
    fin = aujourd_hui + timedelta(days=jours)
    jusqu_a_fin = sum(e.montant for e in dossier.echeances if e.date_limite <= fin)
    return max(jusqu_a_fin - max(exigible(dossier, aujourd_hui), dossier.paye), 0)


def reste_du(dossier: Dossier) -> int:
    """Reste à payer ; rien pour un dossier dispensé."""
    return 0 if dossier.dispense else dossier.reste


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
