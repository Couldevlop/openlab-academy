"""Domaine : équipe de correction, découplée de la chaîne (titulaires, suppléants ordonnés, responsable).

Une équipe par niveau : globale, cours, cohorte ou exercice. La résolution suit l'ordre de priorité des réglages
(exercice > cohorte > cours > global), champ par champ : un champ vide est hérité du niveau moins spécifique. Sans
équipe, les titulaires sont les formateurs LMS de la cohorte ou du cours, sans suppléant ni responsable (le
responsable pédagogique de la console s'applique alors).
"""
from collections.abc import Iterable
from dataclasses import dataclass

from openlab_academy.domain.reglages import ReglagesInvalides

NIVEAUX = ("global", "cours", "cohorte", "exercice")


@dataclass(frozen=True)
class Equipe:
    cours: str | None = None
    cohorte: str | None = None
    exercice: str | None = None
    titulaires: tuple[str, ...] = ()  # dans l'ordre
    suppleants: tuple[str, ...] = ()  # sollicités dans l'ordre quand le formateur dépasse son délai
    responsable: str = ""

    def __post_init__(self):
        if sum(c is not None for c in (self.cours, self.cohorte, self.exercice)) > 1:
            raise ReglagesInvalides("une équipe vise une seule cible : cours, cohorte ou exercice (aucune : globale)")
        if not (self.titulaires or self.suppleants or self.responsable):
            raise ReglagesInvalides("une équipe porte au moins un titulaire, un suppléant ou un responsable")
        membres = [*self.titulaires, *self.suppleants]
        doublons = sorted({m for m in membres if membres.count(m) > 1})
        if doublons:
            raise ReglagesInvalides(f"membre présent deux fois dans l'équipe : {', '.join(doublons)}")

    @property
    def niveau(self) -> int:
        """0 global, 1 cours, 2 cohorte, 3 exercice : plus le niveau est haut, plus l'équipe est spécifique."""
        return 3 if self.exercice else 2 if self.cohorte else 1 if self.cours else 0

    @property
    def libelle(self) -> str:
        cible = self.exercice or self.cohorte or self.cours
        return f"{NIVEAUX[self.niveau]} {cible}" if cible else "global"

    def vise(self, cours: str | None, cohorte: str | None, exercice: str | None) -> bool:
        if self.exercice:
            return self.exercice == exercice
        if self.cohorte:
            return self.cohorte == cohorte
        if self.cours:
            return self.cours == cours
        return True


@dataclass(frozen=True)
class EquipeEffective:
    titulaires: tuple[str, ...]
    suppleants: tuple[str, ...]
    responsable: str  # vide : le responsable pédagogique de la console
    provenance: dict[str, str]  # champ -> niveau qui l'a fourni


def resoudre_equipe(equipes: Iterable[Equipe], cours: str | None, cohorte: str | None, exercice: str | None,
                    titulaires_lms: tuple[str, ...]) -> EquipeEffective:
    applicables = sorted((e for e in equipes if e.vise(cours, cohorte, exercice)), key=lambda e: -e.niveau)

    def champ(nom: str, defaut, source_defaut: str):
        for e in applicables:
            if getattr(e, nom):
                return getattr(e, nom), e.libelle
        return defaut, source_defaut

    titulaires, depuis_titulaires = champ("titulaires", tuple(titulaires_lms), "formateurs LMS")
    suppleants, depuis_suppleants = champ("suppleants", (), "aucun")
    responsable, depuis_responsable = champ("responsable", "", "aucun")
    return EquipeEffective(titulaires, suppleants, responsable, {"titulaires": depuis_titulaires,
                                                                  "suppleants": depuis_suppleants,
                                                                  "responsable": depuis_responsable})
