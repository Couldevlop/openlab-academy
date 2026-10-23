"""Parcours gratuits (MOOC) : ni tarif, ni dossier, ni rappel, ni blocage.

Un parcours devenu gratuit (décision de l'administrateur) dispense ses dossiers qui ont encore quelque chose à payer
(journalisés, motif « parcours devenu gratuit ») : ils ne bloquent plus, ne reçoivent plus de rappels et restent
visibles, dispensés, dans l'historique de l'intendance ; un dossier soldé reste soldé. Un parcours redevenu payant ne
vaut que pour les nouveaux inscrits : aucun dossier rétroactif, les dispenses restent."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from openlab_academy.application.ports_paiement import (
    DossiersADispenser, Inscriptions, Journal, ParcoursGratuits, Tarifs)
from openlab_academy.domain.dossier_paiement import reste_du, statut

MOTIF_GRATUIT = "parcours devenu gratuit"
ACTION_GRATUIT = "dispense_parcours_gratuit"


class TarifSurParcoursGratuit(ValueError):
    pass


class DispenseReservee(PermissionError):
    pass


@dataclass(frozen=True)
class Bilan:
    dispenses: int
    tarif_ignore: bool  # un tarif existe sur le parcours gratuit : il ne s'applique plus


def refuser_tarif_si_gratuit(gratuits: ParcoursGratuits, cours: str) -> None:
    if gratuits.gratuit(cours):
        raise TarifSurParcoursGratuit(
            "Ce parcours est gratuit (MOOC) : aucun tarif ne s'y applique. Décochez « Parcours gratuit (MOOC) » "
            "sur le parcours pour le rendre payant.")


def vue_parcours_gratuit(cours: str, titre: str) -> dict:
    """« Mes paiements » d'un parcours gratuit : un état calme, jamais une erreur."""
    return {"cours": cours, "titre": titre, "gratuit": True}


def etat_gratuit(gratuits: ParcoursGratuits, inscriptions: Inscriptions, apprenant: str, cours: str,
                 titre: Callable[[], str]) -> dict | None:
    """« Mes paiements » : l'état calme d'un parcours gratuit (il prime sur un dossier dispensé d'avant la gratuité),
    pour un apprenant inscrit seulement ; None sinon (le dossier, ou son absence, fait foi)."""
    if gratuits.gratuit(cours) and inscriptions.inscrit(apprenant, cours):
        return vue_parcours_gratuit(cours, titre())
    return None


class DispenserParcoursGratuit:
    """À l'enregistrement d'un parcours : s'il est gratuit, chacun de ses dossiers non dispensés qui a encore quelque
    chose à payer l'est, une ligne de journal par dossier (auteur, date, motif). Réservé à l'administrateur : un autre
    auteur est refusé dès qu'un dossier serait dispensé. Rejouable sans effet."""

    def __init__(self, depot: DossiersADispenser, journal: Journal, gratuits: ParcoursGratuits, tarifs: Tarifs,
                 aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._journal = journal
        self._gratuits = gratuits
        self._tarifs = tarifs
        self._aujourd_hui = aujourd_hui

    def executer(self, acteur: str, cours: str, administrateur: bool = True) -> Bilan:
        if not self._gratuits.gratuit(cours):
            return Bilan(0, False)
        dossiers = [(nom, self._depot.par_nom(nom).dossier) for nom in self._depot.a_dispenser(cours)]
        dossiers = [(nom, d) for nom, d in dossiers if reste_du(d) > 0]  # un dossier soldé reste soldé
        if dossiers and not administrateur:
            raise DispenseReservee("Seul l'administrateur peut rendre gratuit un parcours qui a des dossiers de "
                                   "paiement en cours.")
        for nom, d in dossiers:
            self._depot.dispenser(nom)
            self._journal(nom, acteur, ACTION_GRATUIT, {"statut": statut(d, self._aujourd_hui()).value, "paye": d.paye},
                          {"statut": "dispense", "paye": d.paye}, MOTIF_GRATUIT)
        return Bilan(len(dossiers), self._tarifs.charger(cours) is not None)
