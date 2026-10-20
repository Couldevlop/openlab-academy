"""Cas d'usage : une soumission LMS devient une copie figée avec sa grille ; une re-soumission crée une nouvelle version.

Rien ne bloque l'apprenant : si l'instantané du dépôt échoue, la copie est créée sans contenu et poursuit sa chaîne.
"""
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from openlab_academy.domain.copie import Copie, Proposition, Source, Statut, TransitionInterdite, etape_suivante
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine, ReglagesEvaluation, Surcharge, TypeExercice


@dataclass(frozen=True)
class Exercice:
    """Ce que la publication a figé pour un exercice : son type, sa grille et sa chaîne propre (YAML) éventuelle."""

    type_: TypeExercice
    grille: Grille
    chaine: Chaine | None = None


@dataclass(frozen=True)
class Contenu:
    """Contenu rendu : texte (ou instantané du dépôt), lien source, commit, signature du rendu et soumission LMS."""

    texte: str
    source_url: str
    commit: str
    signature: str
    soumission: str

    @staticmethod
    def signature_de(soumission: dict) -> str:
        """Empreinte de ce que l'apprenant a rendu : une correction du formateur ne la change pas."""
        brut = "\x1f".join(str(soumission.get(c) or "") for c in ("type", "answer", "assignment_attachment"))
        return hashlib.sha256(brut.encode("utf-8")).hexdigest()


class DepotCopies(Protocol):
    """Port de persistance des copies, de leurs propositions et de leurs relectures."""

    def exercice(self, exercice: str) -> Exercice | None: ...
    def cohorte(self, apprenant: str, exercice: str) -> str | None: ...
    def auto_evaluation(self, apprenant: str, exercice: str) -> dict[str, int] | None: ...
    def signature(self, copie_id: str) -> str: ...
    def copie(self, copie_id: str) -> Copie: ...
    def creer(self, copie: Copie, grille: Grille, contenu: Contenu) -> str: ...
    def version_courante(self, soumission: str) -> Copie | None: ...
    def ajouter_proposition(self, copie_id: str, p: Proposition) -> None: ...
    def propositions(self, copie_id: str) -> list[Proposition]: ...
    def changer_statut(self, copie_id: str, statut: Statut, etape: str, echeance: datetime | None) -> None: ...
    def annuler_relectures(self, copie_id: str) -> None: ...


class Instantane(Protocol):
    """Port : photographie d'un dépôt rendu par URL -> (contenu, commit)."""

    def prendre(self, url: str) -> tuple[str, str]: ...


class SoumettreCopie:
    def __init__(self, depot: DepotCopies, instantane: Instantane, reglages: ReglagesEvaluation,
                 horloge: Callable[[], datetime], surcharges: Callable[[], tuple[Surcharge, ...]] = lambda: ()):
        self._depot = depot
        self._instantane = instantane
        self._reglages = reglages
        self._horloge = horloge
        self._surcharges = surcharges

    def executer(self, soumission: dict) -> str | None:
        """Identifiant de la copie courante ; None si l'exercice n'a pas de grille OpenLab."""
        exercice = self._depot.exercice(soumission["assignment"])
        if exercice is None:
            return None
        courante = self._depot.version_courante(soumission["name"])
        signature = Contenu.signature_de(soumission)
        if courante is not None and self._depot.signature(courante.id) == signature:
            return courante.id
        if courante is not None:
            self._remplacer(courante)
        return self._creer(soumission, exercice, signature, 1 if courante is None else courante.version + 1)

    def _remplacer(self, ancienne: Copie) -> None:
        self._depot.annuler_relectures(ancienne.id)
        try:
            self._depot.changer_statut(ancienne.id, ancienne.passer_a(Statut.RENVOYEE).statut, "", None)
        except TransitionInterdite:
            pass  # copie déjà avancée : elle garde son statut, seule la nouvelle version fait foi

    def _creer(self, soumission: dict, exercice: Exercice, signature: str, version: int) -> str:
        apprenant, assignment = soumission["member"], soumission["assignment"]
        cohorte = self._depot.cohorte(apprenant, assignment)
        copie = Copie("", apprenant, assignment, cohorte or "", exercice.type_, version, Statut.RENDUE)
        copie_id = self._depot.creer(copie, exercice.grille, self._contenu(soumission, signature))
        chaine = self._reglages.chaine_pour(exercice.type_, cohorte, assignment, self._surcharges(), exercice.chaine)
        etape = etape_suivante(chaine, None)
        echeance = self._horloge() + timedelta(hours=chaine.config(etape).delai_heures)
        self._depot.changer_statut(copie_id, Statut.RENDUE, etape.value, echeance)
        niveaux = self._depot.auto_evaluation(apprenant, assignment)
        if niveaux is not None:
            self._depot.ajouter_proposition(copie_id, Proposition(Source.AUTO_EVALUATION, apprenant, niveaux))
        return copie_id

    def _contenu(self, soumission: dict, signature: str) -> Contenu:
        nom = soumission["name"]
        if soumission["type"] == "Text":
            return Contenu(soumission["answer"] or "", "", "", signature, nom)
        if soumission["type"] != "URL":
            return Contenu("", soumission.get("assignment_attachment") or "", "", signature, nom)
        url = soumission["answer"]
        try:
            texte, commit = self._instantane.prendre(url)
        except Exception:  # un dépôt injoignable ne bloque pas le rendu
            texte, commit = "", ""
        return Contenu(texte, url, commit, signature, nom)
