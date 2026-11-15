"""Offrir un parcours à un apprenant, et revenir en arrière.

La case « Parcours gratuit (MOOC) » ouvre un parcours à tout le monde ; ceci l'ouvre à une personne. L'apprenant
s'inscrit quand même, parce que l'inscription est le moment où la donnée est collectée et gérée : c'est le
paiement qui saute, pas le dossier. Son dossier naît donc comme celui de n'importe quel inscrit, tarif du jour
figé et échéancier calculé, puis se dispense aussitôt. L'intendance garde ainsi la personne, son parcours, ce
qu'il aurait coûté, qui l'a offert et quand.

Retirer la gratuité rend le dossier dû tel qu'il est : échéances d'origine, blocage de nouveau possible. Ce qui
a été payé reste payé, et un dossier soldé n'est pas touché — il n'y a rien à offrir.
"""
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Protocol

from openlab_academy.application.ports_paiement import DossierEnregistre, Journal
from openlab_academy.domain.dossier_paiement import reste_du, statut

MOTIF_OFFERT = "parcours offert"
ACTION_OFFERT = "dispense_parcours_offert"
ACTION_RETRAIT = "retrait_gratuite"
RESERVE = ("Seuls l'administrateur et l'intendant peuvent offrir un parcours à un apprenant, ou revenir "
           "dessus.")


class GratuiteReservee(PermissionError):
    """Un auteur sans droit a tenté d'offrir un parcours, ou de retirer une gratuité."""


class Gratuites(Protocol):
    """Les parcours offerts, un couple (apprenant, parcours) à la fois."""

    def accordee(self, apprenant: str, cours: str) -> bool: ...
    def accorder(self, apprenant: str, cours: str, acteur: str, motif: str = "") -> None: ...
    def retirer(self, apprenant: str, cours: str) -> None: ...
    def apprenants(self, cours: str) -> tuple[str, ...]: ...


class DossiersOfferts(Protocol):
    """Le dossier d'un apprenant sur un parcours, et sa dispense dans les deux sens."""

    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None: ...
    def dispenser(self, nom: str) -> None: ...
    def retablir(self, nom: str) -> None: ...


@dataclass(frozen=True)
class _Cas:
    gratuites: Gratuites
    dossiers: DossiersOfferts
    journal: Journal
    aujourd_hui: Callable[[], date]

    def _exiger_le_droit(self, habilite: bool) -> None:
        if not habilite:
            raise GratuiteReservee(RESERVE)

    def _journaliser(self, enregistre: DossierEnregistre, acteur: str, action: str, dispense_apres: bool,
                     motif: str) -> None:
        """Le journal de l'intendance dit l'état avant et après : la dispense est le seul champ qui bouge."""
        dossier = enregistre.dossier
        self.journal(enregistre.nom, acteur, action,
                     {"statut": self._statut(dossier, dossier.dispense), "paye": dossier.paye},
                     {"statut": self._statut(dossier, dispense_apres), "paye": dossier.paye}, motif)

    def _statut(self, dossier, dispense: bool) -> str:
        return statut(replace(dossier, dispense=dispense), self.aujourd_hui()).value


class AccorderGratuite(_Cas):
    """Offre le parcours à l'apprenant. Son dossier, s'il en a déjà un avec quelque chose à payer, est dispensé
    et journalisé ; sinon la gratuité attend son inscription, qui ouvrira un dossier déjà offert."""

    def executer(self, acteur: str, apprenant: str, cours: str, habilite: bool, motif: str = "") -> bool:
        self._exiger_le_droit(habilite)
        if self.gratuites.accordee(apprenant, cours):
            return False
        self.gratuites.accorder(apprenant, cours, acteur, motif)
        enregistre = self.dossiers.charger(apprenant, cours)
        if enregistre is not None and reste_du(enregistre.dossier) > 0:
            self.dossiers.dispenser(enregistre.nom)
            self._journaliser(enregistre, acteur, ACTION_OFFERT, True, motif or MOTIF_OFFERT)
        return True


class RetirerGratuite(_Cas):
    """Rend le parcours payant pour cet apprenant : son dossier dispensé redevient dû, tel qu'il est."""

    def executer(self, acteur: str, apprenant: str, cours: str, habilite: bool, motif: str = "") -> bool:
        self._exiger_le_droit(habilite)
        if not self.gratuites.accordee(apprenant, cours):
            return False
        self.gratuites.retirer(apprenant, cours)
        enregistre = self.dossiers.charger(apprenant, cours)
        if enregistre is not None and enregistre.dossier.dispense:
            self.dossiers.retablir(enregistre.nom)
            self._journaliser(enregistre, acteur, ACTION_RETRAIT, False, motif or MOTIF_OFFERT)
        return True
