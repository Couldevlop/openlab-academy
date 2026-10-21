"""Cas d'usage : une soumission LMS devient une copie figée avec sa grille ; une re-soumission crée une nouvelle version.

Rien ne bloque l'apprenant : le rendu n'attend jamais le réseau, l'instantané d'un dépôt est pris en tâche de fond.
Chaque copie reçoit un accusé de dépôt (horodatage UTC et empreinte SHA-256 de ce qui a été rendu). Au-delà du débit
réglé dans la console, un nouveau rendu est refusé.
"""
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from openlab_academy.domain.copie import (
    Copie, CopieVerrouillee, EtatInstantane, Proposition, Source, Statut, etape_suivante, refus_de_resoumission)
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine, ReglagesEvaluation, Surcharge, TypeExercice

SYSTEME = "systeme"


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
    instantane: EtatInstantane = EtatInstantane.SANS
    depose_le: datetime | None = None  # UTC, horodatage de l'accusé de dépôt

    @property
    def rendu_par_lien(self) -> bool:
        """Rendu en URL (dépôt) ; une pièce jointe est un chemin du site (« /files/… »), un texte n'a pas de lien."""
        return bool(self.source_url) and not self.source_url.startswith("/")

    @staticmethod
    def signature_de(soumission: dict) -> str:
        """Empreinte de ce que l'apprenant a rendu : une correction du formateur ne la change pas."""
        brut = "\x1f".join(str(soumission.get(c) or "") for c in ("type", "answer", "assignment_attachment"))
        return hashlib.sha256(brut.encode("utf-8")).hexdigest()


class DepotCopies(Protocol):
    """Port de persistance des copies, de leurs propositions et de leurs relectures."""

    def exercice(self, exercice: str) -> Exercice | None: ...
    def echeance(self, exercice: str) -> datetime | None: ...  # échéance de l'exercice, s'il en a une
    def cohorte(self, apprenant: str, exercice: str) -> str | None: ...
    def auto_evaluation(self, apprenant: str, exercice: str) -> dict[str, int] | None: ...
    def signature(self, copie_id: str) -> str: ...
    def copie(self, copie_id: str) -> Copie: ...
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...  # verrou de ligne + lecture à jour
    def creer(self, copie: Copie, grille: Grille, contenu: Contenu) -> str: ...
    def rendus_depuis(self, apprenant: str, depuis: datetime) -> int: ...  # copies créées pour l'apprenant
    def version_courante(self, soumission: str, verrouillee: bool = False) -> Copie | None: ...
    def ajouter_proposition(self, copie_id: str, p: Proposition) -> None: ...
    def propositions(self, copie_id: str) -> list[Proposition]: ...
    def changer_statut(self, copie_id: str, statut: Statut, etape: str, echeance: datetime | None) -> None: ...
    def annuler_relectures(self, copie_id: str) -> None: ...


class RenduRefuse(Exception):
    """Le rendu dépasse le débit réglé dans la console : refusé, la copie en cours reste inchangée."""


class SoumettreCopie:
    def __init__(self, depot: DepotCopies, reglages: ReglagesEvaluation,
                 horloge: Callable[[], datetime], surcharges: Callable[[], tuple[Surcharge, ...]] = lambda: (),
                 journal: Callable[[str, str, str, dict, dict], None] = lambda *_: None,
                 demarrer: Callable[[str], None] = lambda _: None,
                 notifier: Callable[[str, str], None] = lambda *_: None,
                 horloge_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._depot = depot
        self._horloge_utc = horloge_utc
        self._reglages = reglages
        self._horloge = horloge
        self._surcharges = surcharges
        self._journal = journal
        self._demarrer = demarrer  # déclenche la chaîne de correction d'une copie nouvellement créée
        self._notifier = notifier

    def executer(self, soumission: dict) -> str | None:
        """Identifiant de la copie courante ; None si l'exercice n'a pas de grille OpenLab."""
        exercice = self._depot.exercice(soumission["assignment"])
        if exercice is None:
            return None
        courante = self._depot.version_courante(soumission["name"])
        if courante is not None:  # verrouillée d'abord, puis ses relectures : même ordre que la chaîne
            verrouillee = self._depot.verrouiller(courante.id)
            # un rendu concurrent a pu créer une version entre-temps : relue à jour, sous verrou
            relue = self._depot.version_courante(soumission["name"], verrouillee=True)
            if relue is not None and relue.id != courante.id:
                verrouillee = self._depot.verrouiller(relue.id)
            courante = verrouillee.copie
        signature = Contenu.signature_de(soumission)
        if courante is not None and self._depot.signature(courante.id) == signature:
            return courante.id
        apprenant, assignment = soumission["member"], soumission["assignment"]
        if courante is not None:
            refus = refus_de_resoumission(courante, self._depot.propositions(courante.id),
                                          self._reglages.resoumission_jusqua, self._horloge(),
                                          self._depot.echeance(assignment))
            if refus:  # la copie en cours reste celle qui est corrigée ; l'apprenant le sait
                self._journal(courante.id, apprenant, refus, {}, {"signature": signature})
                self._notifier(apprenant, f"Votre nouveau rendu de l'exercice {assignment} n'a pas été pris en "
                                          f"compte ({refus.removesuffix(' ignoré')}) : la version précédente reste "
                                          f"celle qui est corrigée.")
                return courante.id
        maximum = self._reglages.remise_par_heure
        if self._depot.rendus_depuis(apprenant, self._horloge() - timedelta(hours=1)) >= maximum:
            raise RenduRefuse(f"Trop de rendus : {maximum} rendus par heure au plus. Réessayez plus tard ; "
                              f"votre rendu précédent reste celui qui est corrigé.")
        # tout ce qui peut échouer est calculé avant la première écriture
        cohorte = self._depot.cohorte(apprenant, assignment)
        # une surcharge ou un YAML devenus invalides ne bloquent pas le rendu : chaîne de secours, formateur seul
        chaine, cause = self._reglages.chaine_effective(exercice.type_, cohorte, assignment, self._surcharges(),
                                                        exercice.chaine)
        etape = etape_suivante(chaine, None)
        echeance = self._horloge() + timedelta(hours=chaine.config(etape).delai_heures)
        if courante is not None:
            self._remplacer(courante)
        copie = Copie("", apprenant, assignment, cohorte or "", exercice.type_,
                      1 if courante is None else courante.version + 1, Statut.RENDUE)
        depose_le = self._horloge_utc().astimezone(timezone.utc).replace(tzinfo=None)
        copie_id = self._depot.creer(copie, exercice.grille, self._contenu(soumission, signature, depose_le))
        self._depot.changer_statut(copie_id, Statut.RENDUE, etape.value, echeance)
        self._journal(copie_id, apprenant, "accusé de dépôt", {},
                      {"depose_le": f"{depose_le:%Y-%m-%dT%H:%M:%S}Z", "empreinte": signature,
                       "algorithme": "SHA-256"})
        if cause:
            self._journal(copie_id, SYSTEME, "chaîne invalide, secours formateur", {},
                          {"type_exercice": exercice.type_.value, "cause": cause})
            responsable = self._reglages.responsable_pedagogique
            if responsable:
                self._notifier(responsable, f"Réglages à revoir : la chaîne de l'exercice {assignment} est invalide "
                                            f"({cause}). Le rendu de {apprenant} part sur la chaîne de secours "
                                            f"(formateur seul).")
        niveaux = self._depot.auto_evaluation(apprenant, assignment)
        if niveaux is not None:
            self._depot.ajouter_proposition(copie_id, Proposition(Source.AUTO_EVALUATION, apprenant, niveaux))
        self._demarrer(copie_id)
        return copie_id

    def _remplacer(self, ancienne: Copie) -> None:
        """L'ancienne version quitte la chaîne (ni étape ni échéance) : remplacée, terminale et en lecture seule,
        ses propositions gardées en historique. Une copie renvoyée le reste."""
        self._depot.annuler_relectures(ancienne.id)
        statut = ancienne.statut if ancienne.statut == Statut.RENVOYEE else ancienne.passer_a(Statut.REMPLACEE).statut
        self._depot.changer_statut(ancienne.id, statut, "", None)

    @staticmethod
    def _contenu(soumission: dict, signature: str, depose_le: datetime) -> Contenu:
        nom = soumission["name"]
        if soumission["type"] == "Text":
            return Contenu(soumission["answer"] or "", "", "", signature, nom, depose_le=depose_le)
        if soumission["type"] != "URL":
            return Contenu("", soumission.get("assignment_attachment") or "", "", signature, nom,
                           depose_le=depose_le)
        # le dépôt est photographié en tâche de fond : le rendu n'attend jamais le réseau
        return Contenu("", soumission["answer"], "", signature, nom, EtatInstantane.EN_COURS, depose_le)
