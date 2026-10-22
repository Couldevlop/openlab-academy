"""Ports du paiement des parcours : dépôt des dossiers, tarifs, réglages et journal."""
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif


@dataclass(frozen=True)
class ReglagesPaiement:
    jour_echeance: int = 10
    inscription_tardive_mois: int = 2


@dataclass(frozen=True)
class NouveauDossier:
    apprenant: str
    cours: str
    cohorte: str
    mode: Mode
    tarif: Tarif
    inscription: date
    echeances: tuple[Echeance, ...]


@dataclass(frozen=True)
class DossierEnregistre:
    nom: str
    apprenant: str
    cours: str
    mode: Mode
    telephone: str
    tarif: Tarif
    debut: date
    fin: date
    dossier: Dossier
    inscription: date


class DepotDossiers(Protocol):
    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None: ...
    def creer(self, d: NouveauDossier) -> str: ...
    def remplacer_echeances(self, nom: str, mode: Mode, echeances: tuple[Echeance, ...]) -> None: ...
    def fixer_telephone(self, nom: str, telephone: str) -> None: ...
    def paye(self, nom: str) -> int: ...
    def fixer_delai(self, nom: str, d: date) -> None: ...


class Tarifs(Protocol):
    def charger(self, cours: str) -> Tarif | None: ...


class Reglages(Protocol):
    def charger(self) -> ReglagesPaiement: ...


class Journal(Protocol):
    def __call__(self, dossier: str, acteur: str, action: str, avant: dict, apres: dict, motif: str = "") -> None: ...
