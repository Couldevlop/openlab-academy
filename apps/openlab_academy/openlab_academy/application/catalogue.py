"""Règles du catalogue limité aux parcours visibles, sans accès à la base : quelles cohortes sont entièrement refusées,
comment un filtre de nom déjà posé se combine à l'exclusion, comment une liste déjà calculée se refiltre."""
from collections.abc import Collection, Iterable, Mapping
from typing import Protocol


class SourceCatalogue(Protocol):
    """Port de lecture du catalogue (adapté sur la base par `infrastructure.catalogue_frappe`)."""

    def noms_correspondants(self, doctype: str, nom) -> list[str]: ...
    def cours_par_cohorte(self, lot: str | None = None) -> Mapping[str, Collection[str]]: ...
    def derniers_parcours_inscrits(self, membre: str, exclus: Collection[str], limite: int) -> list[str]: ...
    def parcours_de_repli(self, exclus: Collection[str], limite: int) -> list[str]: ...
    def dernieres_cohortes_inscrites(self, membre: str, exclus: Collection[str], limite: int) -> list[str]: ...
    def cohortes_a_venir(self, exclus: Collection[str], limite: int) -> list[str]: ...
    def categories_hors(self, exclus: Collection[str]) -> frozenset[str]: ...
    def statistiques_hors(self, exclus: Collection[str]) -> dict[str, int]: ...


def lots_entierement_refuses(cours_par_lot: Mapping[str, Collection[str]], refuses: Collection[str]) -> frozenset[str]:
    """Cohortes dont TOUS les parcours sont refusés (une cohorte sans parcours reste visible)."""
    if not refuses:
        return frozenset()
    return frozenset(lot for lot, cours in cours_par_lot.items() if cours and set(cours) <= set(refuses))


def valeurs_in(valeur) -> list[str]:
    """Valeurs d'un filtre « in » : liste, ou chaîne séparée par des virgules (comme Frappe l'interprète)."""
    if isinstance(valeur, str):
        valeur = [v.strip() for v in valeur.split(",")]
    return [v for v in valeur if v]


def filtre_de_nom(actuel, exclus: Collection[str], source: SourceCatalogue, doctype: str) -> list:
    """Filtre `name` conforme à l'exclusion. Aucun filtre posé : `not in exclus`. Un « in » (liste ou chaîne) est amputé
    des exclus ; tout autre filtre du client est résolu en noms puis amputé."""
    if actuel is None:
        return ["not in", list(exclus)]
    if isinstance(actuel, list | tuple) and len(actuel) == 2 and actuel[0] == "in":
        retenus = valeurs_in(actuel[1])
    else:
        retenus = source.noms_correspondants(doctype, actuel)
    return ["in", [n for n in retenus if n not in exclus]]


def sans_les_exclus(lignes: Iterable[Mapping], exclus: Collection[str], cle: str = "name") -> list:
    return [ligne for ligne in lignes if ligne.get(cle) not in exclus]
