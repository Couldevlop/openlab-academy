"""Domaine : grille d'évaluation (critères pondérés, niveaux descripteurs) et calcul de la note.

Une grille est immuable et vérifiée à la construction : poids totalisant 100, niveaux ordonnés,
codes de critères uniques. Son empreinte identifie de façon stable le contenu exact utilisé pour noter.
"""
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass

from openlab_academy.domain.reglages import CritereBareme

PAS_NOTE = 0.5
EPSILON_ARRONDI = 1e-9  # bruit des flottants : 20,4999999999 vaut 20,5, 20,499999998 non


class GrilleInvalide(ValueError):
    """La grille ou son utilisation est incohérente."""


@dataclass(frozen=True)
class Niveau:
    libelle: str
    descripteur: str
    points: int


@dataclass(frozen=True)
class Critere:
    code: str
    libelle: str
    description: str
    poids: int
    niveaux: tuple[Niveau, ...]
    controles: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.code.strip():
            raise GrilleInvalide("code de critère manquant")
        if self.poids <= 0:
            raise GrilleInvalide(f"critère « {self.code} » : le poids doit être positif")
        if len(self.niveaux) < 2:
            raise GrilleInvalide(f"critère « {self.code} » : au moins 2 niveaux requis")
        points = [n.points for n in self.niveaux]
        if any(b <= a for a, b in zip(points, points[1:])):
            raise GrilleInvalide(f"critère « {self.code} » : les points des niveaux doivent être strictement croissants")


@dataclass(frozen=True)
class Grille:
    criteres: tuple[Critere, ...]

    def __post_init__(self):
        if not self.criteres:
            raise GrilleInvalide("la grille n'a aucun critère")
        codes = [c.code for c in self.criteres]
        for code in codes:
            if codes.count(code) > 1:
                raise GrilleInvalide(f"code de critère « {code} » en double")
        total = sum(c.poids for c in self.criteres)
        if total != 100:
            raise GrilleInvalide(f"grille : total {total} % au lieu de 100 %")

    def vers_dict(self) -> dict:
        return {"criteres": [
            {"code": c.code, "libelle": c.libelle, "description": c.description, "poids": c.poids,
             "niveaux": [{"libelle": n.libelle, "descripteur": n.descripteur, "points": n.points} for n in c.niveaux],
             "controles": list(c.controles)}
            for c in self.criteres]}

    @classmethod
    def depuis_dict(cls, donnees: dict) -> "Grille":
        return cls(tuple(
            Critere(c["code"], c["libelle"], c["description"], c["poids"],
                    tuple(Niveau(n["libelle"], n["descripteur"], n["points"]) for n in c["niveaux"]),
                    tuple(c.get("controles", ())))
            for c in donnees["criteres"]))

    def empreinte(self) -> str:
        canonique = json.dumps(self.vers_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonique.encode("utf-8")).hexdigest()

    def note(self, niveaux: dict[str, int], note_sur: int) -> float:
        """Somme pondérée des niveaux atteints (indice par code de critère), arrondie à 0,5."""
        total = 0.0
        for critere in self.criteres:
            indice = niveaux.get(critere.code)
            if indice is None:
                raise GrilleInvalide(f"niveau manquant pour le critère « {critere.code} »")
            if not 0 <= indice < len(critere.niveaux):
                raise GrilleInvalide(f"critère « {critere.code} » : niveau {indice} inexistant")
            bas, haut = critere.niveaux[0].points, critere.niveaux[-1].points
            total += critere.poids * (critere.niveaux[indice].points - bas) / (haut - bas)
        return arrondi_au_pas(total / 100 * note_sur)


def arrondi_au_pas(note: float) -> float:
    """Au demi-point le plus proche, demi-pas arrondi au supérieur (10,25 -> 10,5), comme le front."""
    return math.floor(note / PAS_NOTE + 0.5 + EPSILON_ARRONDI) * PAS_NOTE


def _code(nom: str) -> str:
    sans_accent = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sans_accent.lower()).strip("_")


def _niveaux(libelles: tuple[str, ...]) -> tuple[Niveau, ...]:
    return tuple(Niveau(libelle, libelle, i) for i, libelle in enumerate(libelles))


def grille_generique(criteres: tuple[tuple[str, int], ...], niveaux: tuple[str, ...]) -> Grille:
    """Grille à partir de (libellé, poids) et de libellés de niveaux (points 0, 1, 2…)."""
    return Grille(tuple(Critere(_code(libelle), libelle, libelle, poids, _niveaux(niveaux))
                        for libelle, poids in criteres))


def grille_projet(bareme: tuple[CritereBareme, ...], controles: dict[str, tuple[str, ...]],
                  niveaux: tuple[str, ...]) -> Grille:
    """Grille d'un projet : un critère par entrée du barème, avec ses contrôles (liste de vérification)."""
    return Grille(tuple(Critere(_code(c.nom), c.nom, c.nom, c.poids, _niveaux(niveaux), tuple(controles.get(c.nom, ())))
                        for c in bareme))
