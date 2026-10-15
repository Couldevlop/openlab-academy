"""Domaine : un parcours certifiant, ses modules hebdomadaires, son portfolio et son capstone.

Aucune dépendance à Frappe ni au format de stockage.
"""
import math
import re
from dataclasses import dataclass
from enum import Enum

PROJETS_PAR_PORTFOLIO = 10
HEURES_PAR_MODULE = 8
RYTHME_HEBDO = 12  # heures de travail apprenant par semaine
TITRE_MAX = 120  # laisse la place aux préfixes (« Projet 10 — ») sous la limite LMS de 140
_SALAIRE = re.compile(r"\d+\s*k\s*€", re.IGNORECASE)


class ParcoursInvalide(ValueError):
    """Un invariant du parcours n'est pas respecté."""


def _titre_court(titre: str) -> None:
    if len(titre) > TITRE_MAX:
        raise ParcoursInvalide(f"titre trop long ({len(titre)} > {TITRE_MAX}) : « {titre[:40]}… »")


class Niveau(Enum):
    GUIDE = "guide"
    SEMI_GUIDE = "semi-guide"
    AUTONOME = "autonome"

    @property
    def libelle(self) -> str:
        return {"guide": "Guidé", "semi-guide": "Semi-guidé", "autonome": "Autonome"}[self.value]


@dataclass(frozen=True)
class Module:
    num: str
    title: str
    contenu: str
    livrable: str


@dataclass(frozen=True)
class Bloc:
    title: str
    modules: tuple[Module, ...]


@dataclass(frozen=True)
class Projet:
    titre: str
    duree_h: int
    niveau: Niveau
    contexte: str
    objectifs: tuple[str, ...]
    fonctionnalites: tuple[str, ...]
    stack: tuple[str, ...]
    criteres_acceptation: tuple[str, ...]
    exigences_specifiques: tuple[str, ...]
    livrables: tuple[str, ...]
    apres_module: str | None = None

    def __post_init__(self):
        _titre_court(self.titre)
        if self.duree_h <= 0:
            raise ParcoursInvalide(f"{self.titre}: duree_h doit être positive")


@dataclass(frozen=True)
class Chapitre:
    """Unité de publication : un bloc de modules ou un projet."""

    titre: str
    modules: tuple[Module, ...] = ()
    projet: Projet | None = None


@dataclass(frozen=True)
class Parcours:
    title: str
    short_introduction: str
    description: str
    tags: tuple[str, ...]
    card_gradient: str
    blocs: tuple[Bloc, ...]
    portfolio: tuple[Projet, ...]
    capstone: Projet

    def __post_init__(self):
        for champ in ("title", "short_introduction", "description"):
            if _SALAIRE.search(getattr(self, champ)):
                raise ParcoursInvalide(f"{champ}: rémunération en k€ interdite")
        for bloc in self.blocs:
            _titre_court(bloc.title)
            for module in bloc.modules:
                _titre_court(module.title)
        nums = [m.num for b in self.blocs for m in b.modules]
        doublons = sorted({n for n in nums if nums.count(n) > 1})
        if doublons:
            raise ParcoursInvalide(f"module '{doublons[0]}' en double")
        if len(self.portfolio) != PROJETS_PAR_PORTFOLIO:
            raise ParcoursInvalide(
                f"portfolio: {PROJETS_PAR_PORTFOLIO} projets attendus, {len(self.portfolio)} trouvés")
        for i, p in enumerate(self.portfolio):
            if p.apres_module is None:
                raise ParcoursInvalide(f"portfolio[{i}].apres_module manquant")
            if p.apres_module not in nums:
                raise ParcoursInvalide(f"portfolio[{i}].apres_module: module '{p.apres_module}' inexistant")
        if self.capstone.apres_module is not None:
            raise ParcoursInvalide("capstone.apres_module doit être vide")

    def charge_horaire(self) -> int:
        """Heures de travail apprenant : modules hebdomadaires + portfolio + capstone."""
        modules = sum(len(b.modules) for b in self.blocs) * HEURES_PAR_MODULE
        return modules + sum(p.duree_h for p in self.portfolio) + self.capstone.duree_h

    def duree_semaines(self, heures_par_semaine: int = RYTHME_HEBDO) -> int:
        if heures_par_semaine <= 0:
            raise ValueError("heures_par_semaine doit être positif")
        return math.ceil(self.charge_horaire() / heures_par_semaine)

    def chapitres(self) -> list[Chapitre]:
        """Ordre de publication : chaque bloc, suivi des projets qui consolident ses modules ; capstone en dernier."""
        resultat = []
        for bloc in self.blocs:
            resultat.append(Chapitre(bloc.title, modules=bloc.modules))
            for module in bloc.modules:
                resultat += [Chapitre(f"Projet {n} — {p.titre}", projet=p)
                             for n, p in enumerate(self.portfolio, start=1) if p.apres_module == module.num]
        resultat.append(Chapitre(f"Capstone — {self.capstone.titre}", projet=self.capstone))
        return resultat
