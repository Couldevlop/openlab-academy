"""Adaptateur : contrôles automatiques d'une copie (longueur minimale, lien et dépôt public, fichiers attendus).

Les fichiers attendus d'un dépôt sont déduits des contrôles de la grille (« Tests automatisés », « CI »,
« .env.example », « Conteneurisé ») ; le README est toujours exigé. Un incident réseau ou d'API lève
DepotIndisponible (l'étape sera « non disponible ») ; seul un défaut de la copie produit un motif.
"""
import re
from dataclasses import dataclass

from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Copie
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import ReglagesEvaluation
from openlab_academy.infrastructure.instantane_depot import (
    DELAI_S, DepotIntrouvable, LienRefuse, client_pour, valider_lien)


@dataclass(frozen=True)
class Attendu:
    libelle: str
    fichier: re.Pattern

    def present(self, chemins: list[str]) -> bool:
        return any(self.fichier.search(c) for c in chemins)


README = Attendu("README", re.compile(r"^readme(\.[a-z0-9]+)?$", re.IGNORECASE))
REGLES = (  # (tournure d'un contrôle de la grille, fichier qu'elle exige)
    (re.compile(r"\btests?\b", re.IGNORECASE),
     Attendu("tests automatisés", re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]+$|[._-](test|spec)\.[^/]+$"
                                             r"|Tests?\.[^/]+$"))),
    (re.compile(r"\bCI\b"),
     Attendu("intégration continue (workflow)", re.compile(r"^\.github/workflows/[^/]+\.ya?ml$|^\.gitlab-ci\.yml$"))),
    (re.compile(r"\.env\.example", re.IGNORECASE), Attendu(".env.example", re.compile(r"(^|/)\.env\.example$"))),
    (re.compile(r"conteneuris|docker", re.IGNORECASE),
     Attendu("Dockerfile ou fichier compose", re.compile(r"(^|/)(Dockerfile|(docker-)?compose\.ya?ml)$"))),
)


def attendus(grille: Grille) -> list[Attendu]:
    """README, puis les fichiers exigés par les contrôles de la grille, sans doublon, dans l'ordre des règles."""
    controles = [c for critere in grille.criteres for c in critere.controles]
    return [README] + [a for tournure, a in REGLES if any(tournure.search(c) for c in controles)]


class ControleurDepots:
    def __init__(self, reglages: ReglagesEvaluation, delai_s: float = DELAI_S, jeton: str = ""):
        self._reglages = reglages
        self._delai = delai_s
        self._jeton = jeton

    def verifier(self, copie: Copie, grille: Grille, contenu: Contenu) -> list[str]:
        if not contenu.source_url:
            return self._longueur(contenu.texte)
        if not contenu.rendu_par_lien:
            return []  # pièce jointe déposée sur la plateforme : le livrable est présent
        try:
            lien = valider_lien(contenu.source_url, self._reglages.hotes_depots)
            client = client_pour(lien, self._delai, self._jeton)
        except LienRefuse as refus:
            return [str(refus)]
        try:
            branche = client.infos()  # public et joignable, même si l'instantané a déjà été pris
            chemins = [c for c, _ in client.arborescence(contenu.commit or client.commit(branche))]
        except DepotIntrouvable as introuvable:
            return [str(introuvable)]
        return [f"fichier attendu absent : {a.libelle}" for a in attendus(grille) if not a.present(chemins)]

    def _longueur(self, texte: str) -> list[str]:
        longueur, minimum = len(texte.strip()), self._reglages.longueur_min_caracteres
        if longueur >= minimum:
            return []
        return [f"copie trop courte : {longueur} caractères pour {minimum} attendus au minimum"]
