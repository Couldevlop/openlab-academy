"""Ports du paiement des parcours : dépôt des dossiers et paiements, tarifs, réglages, journal, passerelle."""
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

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


@dataclass(frozen=True)
class Client:
    """Coordonnées transmises à la passerelle : seulement celles connues."""
    nom: str = ""
    prenom: str = ""
    email: str = ""
    telephone: str = ""


@dataclass(frozen=True)
class Verification:
    statut: Literal["confirme", "echoue", "en_attente"]
    montant: int


@dataclass(frozen=True)
class PaiementEnregistre:
    nom: str
    dossier: str
    montant: int
    statut: str


class ReferenceDejaEnregistree(Exception):
    """Un paiement porte déjà cette référence pour ce moyen."""


class DepotDossiers(Protocol):
    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None: ...
    def par_nom(self, nom: str) -> DossierEnregistre | None: ...
    def creer(self, d: NouveauDossier) -> str: ...
    def remplacer_echeances(self, nom: str, mode: Mode, echeances: tuple[Echeance, ...]) -> None: ...
    def fixer_telephone(self, nom: str, telephone: str) -> None: ...
    def paye(self, nom: str) -> int: ...
    def fixer_delai(self, nom: str, d: date) -> None: ...
    def client(self, apprenant: str) -> Client: ...
    def creer_paiement(self, dossier: str, montant: int, moyen: str, reference: str, statut: str) -> str: ...
    def paiement(self, moyen: str, reference: str) -> PaiementEnregistre | None: ...

    def confirmer_paiement(self, moyen: str, reference: str, montant: int) -> bool:
        """Passe le paiement à `confirme` au montant donné, sous verrou ; False s'il l'était déjà (ou inconnu)."""

    def enregistrer_virement(self, dossier: str, montant: int, reference: str, date_paiement: date,
                             auteur: str) -> None:
        """Paiement `virement` confirmé ; lève ReferenceDejaEnregistree si la référence existe déjà."""

    def marquer_echoue(self, moyen: str, reference: str) -> None: ...

    def paiements_en_attente(self, dossier: str, moyen: str, limite: int) -> tuple[str, ...]:
        """Références des paiements en attente du dossier, les plus récents d'abord."""


class Passerelle(Protocol):
    def disponible(self) -> bool: ...

    def initier(self, transaction: str, montant: int, description: str, client: Client, retour: str,
                notification: str) -> str:
        """URL de la page de paiement."""

    def verifier(self, transaction: str) -> Verification: ...


class Tarifs(Protocol):
    def charger(self, cours: str) -> Tarif | None: ...


class Reglages(Protocol):
    def charger(self) -> ReglagesPaiement: ...


class Journal(Protocol):
    def __call__(self, dossier: str, acteur: str, action: str, avant: dict, apres: dict, motif: str = "") -> None: ...
