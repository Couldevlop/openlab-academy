"""Cas d'usage : instantané du dépôt rendu par lien, pris en tâche de fond après le rendu.

Le rendu de l'apprenant n'attend jamais le réseau : la copie est créée aussitôt, instantané « en cours ». La tâche
de fond photographie le dépôt (commit figé : pairs et formateur ne travaillent jamais sur le dépôt vivant), puis
relance chaque tâche qui l'attendait : les contrôles s'ils sont l'étape courante, la pré-correction dès que la
copie a atteint l'étape IA et tant qu'aucune proposition IA n'existe (l'IA tourne en parallèle des pairs : la
copie a pu quitter l'étape IA, ou l'échéance des contrôles passer, avant la fin de l'instantané). Une copie
terminée (publiée, provisoire, renvoyée, remplacée) ne relance rien. Un hébergeur indisponible ne bloque rien :
l'instantané est marqué indisponible et la chaîne continue. Le travail lent précède le verrou de la copie.
"""
from collections.abc import Callable
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, TACHES, TERMINEES, Journal
from openlab_academy.application.controler import cause
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Copie, CopieVerrouillee, EtatInstantane, Proposition, Source, Statut
from openlab_academy.domain.reglages_evaluation import Chaine, Etape


class Instantane(Protocol):
    """Port : photographie d'un dépôt rendu par URL -> (contenu, commit)."""

    def prendre(self, url: str) -> tuple[str, str]: ...


class DepotInstantanes(Protocol):
    def contenu(self, copie_id: str) -> Contenu: ...
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...
    def completer_contenu(self, copie_id: str, texte: str, commit: str, instantane: EtatInstantane) -> None: ...
    def propositions(self, copie_id: str) -> list[Proposition]: ...


class PrendreInstantane:
    def __init__(self, depot: DepotInstantanes, instantane: Instantane, file: Callable[[str, str], None],
                 chaine: Callable[[Copie], Chaine], journal: Journal = lambda *_: None):
        self._depot = depot
        self._instantane = instantane
        self._file = file
        self._chaine = chaine
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
        if v.copie.statut in TERMINEES or not v.etat.etape:
            return
        etape = Etape(v.etat.etape)
        if etape == Etape.CONTROLES:  # les contrôles attendaient l'instantané : ils reprennent, dans leur délai
            self._file(TACHES[etape], copie_id)
        if self._pre_correction_attendue(v.copie, etape):
            self._file(TACHES[Etape.IA], copie_id)
            if etape != Etape.IA:  # la copie a quitté l'étape IA sans proposition : relance consignée
                self._journal(copie_id, SYSTEME, "pré-correction relancée après l'instantané", {},
                              {"etape": etape.value})

    def _pre_correction_attendue(self, copie: Copie, etape: Etape) -> bool:
        chaine = self._chaine(copie)
        if not chaine.active(Etape.IA):
            return False
        ordre = [c.etape for c in chaine.etapes]
        if ordre.index(etape) < ordre.index(Etape.IA):
            return False  # pas encore atteinte : l'entrée dans l'étape IA la lancera
        return not any(p.source == Source.IA for p in self._depot.propositions(copie.id))
