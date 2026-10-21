"""Cas d'usage : instantané du dépôt rendu par lien, pris en tâche de fond après le rendu.

Le rendu de l'apprenant n'attend jamais le réseau : la copie est créée aussitôt, instantané « en cours ». La tâche
de fond photographie le dépôt (commit figé : pairs et formateur ne travaillent jamais sur le dépôt vivant), puis
relance l'étape qui l'attendait (contrôles ou pré-correction). Un hébergeur indisponible ne bloque rien :
l'instantané est marqué indisponible et la chaîne continue. Le travail lent précède le verrou de la copie.
"""
from collections.abc import Callable
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, TACHES, Journal
from openlab_academy.application.controler import cause
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import CopieVerrouillee, EtatInstantane, Statut
from openlab_academy.domain.reglages_evaluation import Etape


class Instantane(Protocol):
    """Port : photographie d'un dépôt rendu par URL -> (contenu, commit)."""

    def prendre(self, url: str) -> tuple[str, str]: ...


class DepotInstantanes(Protocol):
    def contenu(self, copie_id: str) -> Contenu: ...
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...
    def completer_contenu(self, copie_id: str, texte: str, commit: str, instantane: EtatInstantane) -> None: ...


class PrendreInstantane:
    def __init__(self, depot: DepotInstantanes, instantane: Instantane, file: Callable[[str, str], None],
                 journal: Journal = lambda *_: None):
        self._depot = depot
        self._instantane = instantane
        self._file = file
        self._journal = journal

    def executer(self, copie_id: str) -> None:
        contenu = self._depot.contenu(copie_id)
        if contenu.instantane != EtatInstantane.EN_COURS:
            return
        try:
            texte, commit = self._instantane.prendre(contenu.source_url)
            etat, action, details = EtatInstantane.PRIS, "instantané pris", {"commit": commit}
        except Exception as erreur:  # rien ne bloque : la chaîne continue sans instantané
            texte, commit = "", ""
            etat, action, details = EtatInstantane.INDISPONIBLE, "instantané indisponible", {"cause": cause(erreur)}
        v = self._depot.verrouiller(copie_id)
        if v.copie.statut == Statut.REMPLACEE or self._depot.contenu(copie_id).instantane != EtatInstantane.EN_COURS:
            return  # remplacée par un nouveau rendu, ou instantané déjà tranché par une autre tâche
        self._depot.completer_contenu(copie_id, texte, commit, etat)
        self._journal(copie_id, SYSTEME, action, {}, details)
        etape = Etape(v.etat.etape) if v.etat.etape else None
        if etape in TACHES:  # l'étape attendait l'instantané : elle reprend, dans son propre délai
            self._file(TACHES[etape], copie_id)
