"""Parcours gratuits (MOOC) : ni tarif, ni dossier, ni rappel, ni blocage.

Un parcours devenu gratuit dispense ses dossiers existants (journalisés, motif « parcours devenu gratuit ») : ils ne
bloquent plus, ne reçoivent plus de rappels et restent visibles, dispensés, dans l'historique de l'intendance. Un
parcours redevenu payant ne vaut que pour les nouveaux inscrits : aucun dossier rétroactif, les dispenses restent."""
from collections.abc import Callable
from datetime import date

from openlab_academy.application.ports_paiement import DossiersADispenser, Journal, ParcoursGratuits
from openlab_academy.domain.dossier_paiement import statut

MOTIF_GRATUIT = "parcours devenu gratuit"
ACTION_GRATUIT = "dispense_parcours_gratuit"


class TarifSurParcoursGratuit(ValueError):
    pass


def refuser_tarif_si_gratuit(gratuits: ParcoursGratuits, cours: str) -> None:
    if gratuits.gratuit(cours):
        raise TarifSurParcoursGratuit(
            "Ce parcours est gratuit (MOOC) : aucun tarif ne s'y applique. Décochez « Parcours gratuit (MOOC) » "
            "sur le parcours pour le rendre payant.")


def vue_parcours_gratuit(cours: str, titre: str) -> dict:
    """« Mes paiements » d'un parcours gratuit : un état calme, jamais une erreur."""
    return {"cours": cours, "titre": titre, "gratuit": True}


class DispenserParcoursGratuit:
    """À l'enregistrement d'un parcours : s'il est gratuit, chacun de ses dossiers non dispensés l'est, une ligne
    de journal par dossier (auteur, date, motif). Rejouable sans effet."""

    def __init__(self, depot: DossiersADispenser, journal: Journal, gratuits: ParcoursGratuits,
                 aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._journal = journal
        self._gratuits = gratuits
        self._aujourd_hui = aujourd_hui

    def executer(self, acteur: str, cours: str) -> int:
        """Nombre de dossiers dispensés."""
        if not self._gratuits.gratuit(cours):
            return 0
        noms = self._depot.a_dispenser(cours)
        for nom in noms:
            d = self._depot.par_nom(nom).dossier
            self._depot.dispenser(nom)
            self._journal(nom, acteur, ACTION_GRATUIT, {"statut": statut(d, self._aujourd_hui()).value, "paye": d.paye},
                          {"statut": "dispense", "paye": d.paye}, MOTIF_GRATUIT)
        return len(noms)
