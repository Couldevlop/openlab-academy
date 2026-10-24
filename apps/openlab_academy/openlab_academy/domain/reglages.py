"""Domaine : réglages pédagogiques et organisationnels de la plateforme (modifiables par l'administration).

Les valeurs par défaut sont celles du lancement ; les invariants garantissent qu'aucun réglage incohérent
ne peut être enregistré.
"""
import re
from dataclasses import dataclass, field

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_HEURE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ReglagesInvalides(ValueError):
    """Un réglage est incohérent."""


def _enumerer(mots: list[str]) -> str:
    return mots[0] if len(mots) == 1 else f"{', '.join(mots[:-1])} et {mots[-1]}"


@dataclass(frozen=True)
class Rythme:
    """Format de cohorte : heures de travail apprenant pour chaque jour, du lundi au dimanche."""

    code: str
    libelle: str
    heures_par_jour: tuple[int, ...]

    def __post_init__(self):
        if not self.code.strip():
            raise ReglagesInvalides("code de rythme manquant")
        if len(self.heures_par_jour) != len(JOURS):
            raise ReglagesInvalides(f"rythme « {self.code} » : 7 valeurs attendues (lundi → dimanche)")
        if any(h < 0 for h in self.heures_par_jour):
            raise ReglagesInvalides(f"rythme « {self.code} » : heures négatives")
        if not any(self.heures_par_jour):
            raise ReglagesInvalides(f"rythme « {self.code} » : aucune heure dans la semaine")

    @property
    def heures(self) -> int:
        return sum(self.heures_par_jour)

    @property
    def semaine(self) -> tuple[tuple[str, int], ...]:
        return tuple(zip(JOURS, self.heures_par_jour))

    @property
    def descriptif(self) -> str:
        groupes: dict[int, list[str]] = {}
        for jour, heures in self.semaine:
            if heures:
                groupes.setdefault(heures, []).append(jour)
        parties = [f"{h} h {'le' if len(j) == 1 else 'les'} {_enumerer(j)}" for h, j in groupes.items()]
        return f"{self.heures} h par semaine : {', '.join(parties)}"


@dataclass(frozen=True)
class CritereBareme:
    nom: str
    poids: int


BAREME_DEFAUT = (CritereBareme("Fonctionnel", 40), CritereBareme("Qualité & tests", 25),
                 CritereBareme("Architecture", 15), CritereBareme("Sécurité", 10), CritereBareme("Documentation", 10))
EXIGENCES_DEFAUT = (
    "README : installation, architecture, choix techniques",
    "Tests automatisés, couverture ≥ 70 %",
    "Lint, formatage et typage vérifiés",
    "CI GitHub Actions verte",
    "Conteneurisé : démarre en une commande",
    "Secrets hors du code (.env.example fourni)",
    "Sécurité OWASP de base",
    "Architecture propre : domaine séparé de l'infrastructure",
    "Commits conventionnels",
    "Décisions documentées (ADR)",
)
RYTHMES_DEFAUT = (
    Rythme("standard", "Standard", (2, 0, 2, 0, 2, 3, 3)),
    Rythme("intensif", "Intensif", (2, 2, 2, 2, 2, 3, 3)),
)


@dataclass(frozen=True)
class Reglages:
    projets_par_portfolio: int = 10
    heures_par_module: int = 8
    delai_ouverture_semaines: int = 2
    jour_ouverture: int = 0  # 0 = lundi … 6 = dimanche
    questions_par_quiz: int = 5
    tentatives_max: int = 3
    score_min: int = 100  # % de bonnes réponses exigé pour valider la leçon
    delai_exercices_minutes: int = 60  # délai entre l'ouverture d'une leçon et l'accès aux exercices
    bareme: tuple[CritereBareme, ...] = BAREME_DEFAUT
    exigences_communes: tuple[str, ...] = EXIGENCES_DEFAUT
    rythmes: tuple[Rythme, ...] = field(default=RYTHMES_DEFAUT)
    heure_debut: str = "18:30"
    heure_fin: str = "20:30"
    fuseau: str = "Africa/Abidjan"
    parcours_pilote: str = "Fondamentaux de la Data Science"
    formateur: str = "Administrator"
    places_par_cohorte: int = 30  # sans places, le LMS n'offre pas l'inscription autonome

    def __post_init__(self):
        for champ in ("projets_par_portfolio", "heures_par_module", "questions_par_quiz", "tentatives_max",
                      "places_par_cohorte"):
            if getattr(self, champ) <= 0:
                raise ReglagesInvalides(f"{champ} doit être positif")
        if not 1 <= self.score_min <= 100:
            raise ReglagesInvalides("score_min entre 1 et 100 %")
        if self.delai_exercices_minutes < 0:
            raise ReglagesInvalides("delai_exercices_minutes ne peut pas être négatif")
        if self.delai_ouverture_semaines < 0:
            raise ReglagesInvalides("delai_ouverture_semaines ne peut pas être négatif")
        if not 0 <= self.jour_ouverture <= 6:
            raise ReglagesInvalides("jour_ouverture doit désigner un jour de 0 (lundi) à 6 (dimanche)")
        for champ in ("parcours_pilote", "formateur", "fuseau"):
            if not getattr(self, champ).strip():
                raise ReglagesInvalides(f"{champ} manquant")
        self._verifier_bareme()
        self._verifier_rythmes()
        for heure in (self.heure_debut, self.heure_fin):
            if not _HEURE.match(heure):
                raise ReglagesInvalides(f"heure « {heure} » invalide (format HH:MM)")
        if self.heure_fin <= self.heure_debut:
            raise ReglagesInvalides("la séance doit finir après son début")

    def _verifier_bareme(self) -> None:
        for critere in self.bareme:
            if critere.poids < 0:
                raise ReglagesInvalides(f"barème : poids négatif pour « {critere.nom} »")
        total = sum(c.poids for c in self.bareme)
        if total != 100:
            raise ReglagesInvalides(f"barème : total {total} % au lieu de 100 %")

    def _verifier_rythmes(self) -> None:
        if not self.rythmes:
            raise ReglagesInvalides("il faut au moins un rythme de cohorte")
        codes = [r.code for r in self.rythmes]
        for code in codes:
            if codes.count(code) > 1:
                raise ReglagesInvalides(f"code de rythme « {code} » en double")

    def rythme(self, code: str) -> Rythme:
        for r in self.rythmes:
            if r.code == code:
                return r
        raise ReglagesInvalides(f"rythme « {code} » inconnu : {[r.code for r in self.rythmes]}")
