"""Domaine : copie rendue, propositions de notation, médiane, écarts et lots de relecture.

La copie suit une machine à états ; une copie renvoyée n'avance plus (un nouveau dépôt crée une nouvelle version).
Un nouveau rendu remplace la copie en cours : elle devient REMPLACEE, terminale et en lecture seule.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from openlab_academy.domain.reglages_evaluation import Chaine, Etape, Resoumission, TypeExercice


class TransitionInterdite(ValueError):
    """Le changement de statut demandé n'est pas autorisé."""


class Statut(str, Enum):
    RENDUE = "rendue"
    RENVOYEE = "renvoyee"
    CONTROLEE = "controlee"
    PRE_CORRIGEE = "pre_corrigee"
    EN_RELECTURE = "en_relecture"
    A_CORRIGER = "a_corriger"
    PROVISOIRE = "provisoire"
    PUBLIEE = "publiee"
    REMPLACEE = "remplacee"


class EtatInstantane(str, Enum):
    """Instantané du dépôt rendu par lien, pris en tâche de fond après le rendu."""

    SANS = ""  # rendu texte ou fichier : rien à photographier
    EN_COURS = "en_cours"  # contrôles et pré-correction l'attendent (dans leurs propres délais)
    PRIS = "pris"
    INDISPONIBLE = "indisponible"  # hébergeur injoignable : la chaîne continue sans instantané


class Source(str, Enum):
    AUTO_EVALUATION = "auto_evaluation"
    CONTROLES = "controles"
    IA = "ia"
    PAIR = "pair"
    JURY = "jury"
    FORMATEUR = "formateur"


_S = Statut
TRANSITIONS: dict[Statut, frozenset[Statut]] = {
    _S.RENDUE: frozenset({_S.CONTROLEE, _S.RENVOYEE, _S.PRE_CORRIGEE, _S.EN_RELECTURE, _S.A_CORRIGER, _S.REMPLACEE}),
    _S.RENVOYEE: frozenset(),
    _S.CONTROLEE: frozenset({_S.PRE_CORRIGEE, _S.EN_RELECTURE, _S.A_CORRIGER, _S.REMPLACEE}),
    _S.PRE_CORRIGEE: frozenset({_S.EN_RELECTURE, _S.A_CORRIGER, _S.REMPLACEE}),
    _S.EN_RELECTURE: frozenset({_S.A_CORRIGER, _S.REMPLACEE}),
    _S.A_CORRIGER: frozenset({_S.PROVISOIRE, _S.PUBLIEE, _S.REMPLACEE}),
    _S.PROVISOIRE: frozenset({_S.PUBLIEE, _S.REMPLACEE}),
    _S.PUBLIEE: frozenset(),
    _S.REMPLACEE: frozenset(),
}
HUMAINES = (Source.JURY, Source.FORMATEUR)


@dataclass(frozen=True)
class Proposition:
    source: Source
    auteur: str
    niveaux: dict[str, int]
    commentaires: dict[str, str] = field(default_factory=dict)
    citations: dict[str, str] = field(default_factory=dict)
    confiance: float | None = None
    au_nom_de: str | None = None


@dataclass(frozen=True)
class Copie:
    id: str
    apprenant: str
    exercice: str
    cohorte: str
    type_: TypeExercice
    version: int
    statut: Statut

    def passer_a(self, statut: Statut) -> "Copie":
        if statut not in TRANSITIONS[self.statut]:
            raise TransitionInterdite(f"copie {self.id} : {self.statut.value} → {statut.value} interdit")
        return replace(self, statut=statut)


@dataclass(frozen=True)
class Etat:
    """Où en est la copie dans sa chaîne : étape courante, échéance, destinataire d'une escalade, butoir de
    l'étape des pairs (au-delà, aucune relecture n'est plus attendue)."""

    etape: str
    echeance: datetime | None
    escalade_a: str = ""
    butoir: datetime | None = None
    souffrance_depuis: datetime | None = None  # escalade épuisée : la copie attend un humain, sans recours
    rappel_souffrance: datetime | None = None  # dernier rappel au responsable (au plus un par jour)


@dataclass(frozen=True)
class CopieVerrouillee:
    """Copie et état relus par une lecture verrouillante : la dernière version validée, pas un instantané."""

    copie: Copie
    etat: Etat


def refus_de_resoumission(courante: Copie, props: list[Proposition], regle: Resoumission, maintenant: datetime,
                          echeance: datetime | None) -> str | None:
    """Motif pour lequel un nouveau rendu ne remplace pas la copie courante, ou None s'il la remplace.

    Une note publiée est définitive. Une copie renvoyée attend justement un nouveau rendu : il est toujours accepté.
    Sinon, selon la console : jusqu'au premier geste humain de correction (note du formateur ou d'un juré,
    publication provisoire), ou jusqu'à l'échéance de l'exercice (sans échéance : toujours)."""
    if courante.statut == Statut.PUBLIEE:
        return "rendu après publication ignoré"
    if courante.statut == Statut.RENVOYEE:
        return None
    if regle == Resoumission.ECHEANCE:
        return "rendu après l'échéance ignoré" if echeance is not None and maintenant > echeance else None
    if courante.statut == Statut.PROVISOIRE or any(p.source in HUMAINES for p in props):
        return "rendu après le début de la correction ignoré"
    return None


def etape_suivante(chaine: Chaine, apres: Etape | None) -> Etape:
    """Prochaine étape active après `apres` (None = début de chaîne) ; le formateur clôt toujours la chaîne."""
    ordre = list(Etape)
    debut = 0 if apres is None else ordre.index(apres) + 1
    for etape in ordre[debut:]:
        if chaine.active(etape):
            return etape
    raise ValueError("aucune étape après le formateur")


def mediane(props: list[Proposition]) -> dict[str, int]:
    """Médiane par critère (médiane basse si le nombre de valeurs est pair)."""
    valeurs: dict[str, list[int]] = {}
    for p in props:
        for critere, niveau in p.niveaux.items():
            valeurs.setdefault(critere, []).append(niveau)
    return {c: sorted(v)[(len(v) - 1) // 2] for c, v in valeurs.items()}


def ecarts(props: list[Proposition], seuil: int = 1) -> set[str]:
    """Critères où deux sources diffèrent de plus que le seuil."""
    valeurs: dict[str, list[int]] = {}
    for p in props:
        for critere, niveau in p.niveaux.items():
            valeurs.setdefault(critere, []).append(niveau)
    return {c for c, v in valeurs.items() if max(v) - min(v) > seuil}


def nb_pairs_possible(demande: int, taille_cohorte: int) -> int:
    return max(0, min(demande, taille_cohorte - 1))


def lots(copies_ia: dict[str, Proposition], seuil: float) -> list[list[str]]:
    """Regroupe les copies de même vecteur de niveaux IA (confiance ≥ seuil) ; un lot compte au moins 2 copies."""
    groupes: dict[tuple, list[str]] = {}
    for copie_id, p in copies_ia.items():
        if p.confiance is not None and p.confiance >= seuil:
            groupes.setdefault(tuple(sorted(p.niveaux.items())), []).append(copie_id)
    return [ids for ids in groupes.values() if len(ids) > 1]
