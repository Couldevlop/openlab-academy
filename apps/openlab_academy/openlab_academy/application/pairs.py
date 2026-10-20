"""Cas d'usage : relecture par les pairs (modèle Coursera) dans la cohorte.

Les relecteurs sont tirés des copies du même exercice et de la même cohorte : on ne relit qu'un exercice qu'on a
soi-même rendu, jamais sa propre copie, jamais deux fois la même. Les données renvoyées ne nomment pas les auteurs.
"""
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol

from openlab_academy.domain.copie import Copie, CopieVerrouillee, Proposition, Source, Statut
from openlab_academy.domain.grille import Grille, GrilleInvalide
from openlab_academy.domain.reglages_evaluation import Etape


class RelectureRefusee(ValueError):
    """La relecture demandée n'est pas permise."""


class StatutRelecture(str, Enum):
    A_FAIRE = "à_faire"
    FAITE = "faite"
    REATTRIBUEE = "réattribuée"
    ANNULEE = "annulée"


ACTIVES = (StatutRelecture.A_FAIRE, StatutRelecture.FAITE)


@dataclass(frozen=True)
class Relecture:
    id: str
    copie: str
    relecteur: str
    statut: StatutRelecture
    echeance: datetime | None
    rappelee: bool = False


class DepotRelectures(Protocol):
    """Port de persistance des relectures entre pairs."""

    def copies_rendues(self, exercice: str, cohorte: str) -> list[Copie]: ...  # version courante, non renvoyée
    def taille_cohorte(self, cohorte: str) -> int: ...
    def relectures(self, exercice: str, cohorte: str) -> list[Relecture]: ...
    def relecture(self, relecture_id: str) -> Relecture | None: ...
    def verrouiller_relecture(self, relecture_id: str) -> Relecture | None: ...  # lue et verrouillée
    def relectures_copie(self, copie_id: str) -> list[Relecture]: ...  # lues et verrouillées
    def relectures_echues(self, maintenant: datetime) -> list[Relecture]: ...
    def attribuer(self, copie_id: str, relecteur: str, echeance: datetime) -> str | None: ...  # None : paire déjà là
    def changer_statut_relecture(self, relecture_id: str, statut: StatutRelecture) -> None: ...
    def rappeler(self, relecture_id: str, echeance: datetime) -> None: ...
    def dispenser(self, copie_id: str) -> None: ...


class AttribuerPairs:
    def __init__(self, depot: DepotRelectures, horloge: Callable[[], datetime]):
        self._depot = depot
        self._horloge = horloge

    def executer(self, copie: Copie, cohorte_rendue: list[Copie], n: int, delai_heures: int) -> tuple[str, ...]:
        """L'auteur reçoit jusqu'à n copies à relire, et sa copie jusqu'à n relecteurs parmi ceux qui ont rendu.

        Renvoie les relectures confiées à l'auteur (identifiants seuls : ni auteur, ni relecteur).
        """
        toutes = self._depot.relectures(copie.exercice, copie.cohorte)
        deja = {(r.relecteur, r.copie) for r in toutes}
        actives = [r for r in toutes if r.statut in ACTIVES]
        recues = Counter(r.copie for r in actives)
        charge = Counter(r.relecteur for r in actives)
        echeance = self._horloge() + timedelta(hours=delai_heures)
        auteur = copie.apprenant
        a_relire = sorted((c for c in cohorte_rendue
                           if c.statut == Statut.EN_RELECTURE and c.apprenant != auteur
                           and (auteur, c.id) not in deja and recues[c.id] < n),
                          key=lambda c: (recues[c.id], c.id))
        confiees = []
        for c in a_relire:
            if charge[auteur] >= n:
                break
            relecture = self._depot.attribuer(c.id, auteur, echeance)
            if relecture is not None:  # None : une attribution concurrente a déjà créé cette paire
                confiees.append(relecture)
                charge[auteur] += 1
        relecteurs = sorted({c.apprenant for c in cohorte_rendue if c.apprenant != auteur
                             and (c.apprenant, copie.id) not in deja and charge[c.apprenant] < n},
                            key=lambda a: (charge[a], a))
        for relecteur in relecteurs:
            if recues[copie.id] >= n:
                break
            if self._depot.attribuer(copie.id, relecteur, echeance) is not None:
                recues[copie.id] += 1
        return tuple(confiees)

    def reattribuer(self, copie: Copie, cohorte_rendue: list[Copie], delai_heures: int) -> str | None:
        """Confie la copie au pair le moins chargé qui ne l'a jamais eue ; None si personne n'est disponible."""
        toutes = self._depot.relectures(copie.exercice, copie.cohorte)
        exclus = {copie.apprenant} | {r.relecteur for r in toutes if r.copie == copie.id}
        charge = Counter(r.relecteur for r in toutes if r.statut in ACTIVES)
        echeance = self._horloge() + timedelta(hours=delai_heures)
        for candidat in sorted({c.apprenant for c in cohorte_rendue} - exclus, key=lambda a: (charge[a], a)):
            if self._depot.attribuer(copie.id, candidat, echeance) is not None:
                return candidat
        return None


class DepotCopiesRelues(Protocol):
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...
    def grille(self, copie_id: str) -> Grille: ...
    def ajouter_proposition(self, copie_id: str, p: Proposition) -> None: ...


class Avanceur(Protocol):
    def pairs_requis(self, copie: Copie) -> int: ...
    def executer(self, copie_id: str, terminee: Etape | None = None) -> None: ...


class EnregistrerRelecture:
    def __init__(self, depot: DepotCopiesRelues, relectures: DepotRelectures, avanceur: Avanceur,
                 journal: Callable[[str, str, str, dict, dict], None] = lambda *_: None):
        self._depot = depot
        self._relectures = relectures
        self._avanceur = avanceur
        self._journal = journal

    def executer(self, relecteur: str, relecture_id: str, niveaux: dict[str, int],
                 commentaires: dict[str, str]) -> None:
        r = self._relectures.relecture(relecture_id)
        if r is None or r.relecteur != relecteur:
            raise RelectureRefusee("relecture non attribuée")
        # verrous dans l'ordre copie puis relecture (comme l'échéancier) : un double envoi n'enregistre qu'une fois
        copie = self._depot.verrouiller(r.copie).copie
        r = self._relectures.verrouiller_relecture(relecture_id)
        if r.statut != StatutRelecture.A_FAIRE:
            raise RelectureRefusee("cette relecture n'est plus à faire")
        grille = self._depot.grille(r.copie)
        codes = {c.code for c in grille.criteres}
        if set(niveaux) != codes:
            raise RelectureRefusee("un niveau est attendu pour chaque critère de la grille")
        try:
            grille.note(niveaux, 1)
        except GrilleInvalide as e:
            raise RelectureRefusee(f"niveau invalide : {e}") from None
        nets = {c: str(commentaires.get(c) or "").strip() for c in codes}
        if not all(nets.values()):
            raise RelectureRefusee("un commentaire est obligatoire pour chaque critère")
        self._depot.ajouter_proposition(r.copie, Proposition(Source.PAIR, relecteur, dict(niveaux), nets))
        self._relectures.changer_statut_relecture(r.id, StatutRelecture.FAITE)
        self._journal(r.copie, relecteur, "relecture", {}, {"relecture": r.id})
        if copie.statut != Statut.EN_RELECTURE:
            return
        # lecture verrouillante après le verrou de la copie : le dernier de deux relecteurs simultanés
        # voit la relecture validée par l'autre et fait avancer la copie
        faites = sum(1 for x in self._relectures.relectures_copie(copie.id) if x.statut == StatutRelecture.FAITE)
        if faites >= self._avanceur.pairs_requis(copie):
            self._avanceur.executer(copie.id, Etape.PAIRS)
