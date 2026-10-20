"""Domaine : réglages de l'évaluation (chaînes d'étapes par type d'exercice, délais, actions à expiration, IA).

Aucune étape ne bloque : chacune a un délai et une action à expiration. Le formateur reste toujours actif,
car seul un humain publie une note définitive.
"""
from dataclasses import dataclass, field
from enum import Enum

from openlab_academy.domain.reglages import ReglagesInvalides

TOURNURES_DEFAUT = (
    "ignore les instructions", "ignore previous instructions", "ignore all previous instructions",
    "donne 20/20", "give full marks", "tu es maintenant", "you are now", "system prompt",
)
GRILLE_GENERIQUE_DEFAUT = (("Pertinence", 30), ("Rigueur", 30), ("Clarté", 20), ("Ancrage dans le contexte ivoirien", 20))
NIVEAUX_GENERIQUES_DEFAUT = ("Insuffisant", "À consolider", "Satisfaisant", "Excellent")


class TypeExercice(str, Enum):
    MISE_EN_SITUATION = "mise_en_situation"
    LIVRABLE = "livrable"
    PROJET = "projet"
    CAPSTONE = "capstone"


class Etape(str, Enum):
    AUTO_EVALUATION = "auto_evaluation"
    CONTROLES = "controles"
    IA = "ia"
    PAIRS = "pairs"
    JURY = "jury"
    FORMATEUR = "formateur"


class Expiration(str, Enum):
    PASSER = "passer"
    REATTRIBUER = "reattribuer"
    ESCALADER = "escalader"
    DISPENSER = "dispenser"
    PUBLIER_PROVISOIRE = "publier_provisoire"


@dataclass(frozen=True)
class ConfigEtape:
    etape: Etape
    active: bool
    delai_heures: int
    expiration: Expiration


@dataclass(frozen=True)
class Chaine:
    etapes: tuple[ConfigEtape, ...]
    nb_pairs: int = 3
    anonymat: bool = True
    note_masquee_avant_relectures: bool = True
    note_sur: int = 20
    seuil_reussite: float = 10.0

    def __post_init__(self):
        if self.nb_pairs < 0:
            raise ReglagesInvalides("nb_pairs ne peut pas être négatif")
        if self.note_sur <= 0:
            raise ReglagesInvalides("note_sur doit être positif")
        if not 0 <= self.seuil_reussite <= self.note_sur:
            raise ReglagesInvalides("seuil_reussite doit être compris entre 0 et la note maximale")
        for c in self.etapes:
            if c.delai_heures < 0:
                raise ReglagesInvalides(f"délai négatif pour l'étape « {c.etape.value} »")
        if not self.active(Etape.FORMATEUR):
            raise ReglagesInvalides("l'étape formateur doit rester active : seul un humain publie une note définitive")

    def vers_dict(self) -> dict:
        return {"etapes": [{"etape": c.etape.value, "active": c.active, "delai_heures": c.delai_heures,
                            "expiration": c.expiration.value} for c in self.etapes],
                "nb_pairs": self.nb_pairs, "anonymat": self.anonymat,
                "note_masquee_avant_relectures": self.note_masquee_avant_relectures,
                "note_sur": self.note_sur, "seuil_reussite": self.seuil_reussite}

    @classmethod
    def depuis_dict(cls, donnees) -> "Chaine":
        """Chaîne décrite par un dictionnaire (YAML d'un exercice) ; les étapes non citées sont inactives."""
        if not isinstance(donnees, dict):
            raise ReglagesInvalides("la chaîne doit être un dictionnaire")
        lignes = donnees.get("etapes")
        if not isinstance(lignes, list) or not lignes:
            raise ReglagesInvalides("la chaîne doit lister ses « etapes »")
        configs = {}
        for i, ligne in enumerate(lignes):
            try:
                etape = Etape(ligne["etape"])
                configs[etape] = ConfigEtape(etape, bool(ligne["active"]), int(ligne["delai_heures"]),
                                             Expiration(ligne["expiration"]))
            except (KeyError, TypeError, ValueError) as e:
                raise ReglagesInvalides(
                    f"etapes[{i}] invalide : etape, active, delai_heures et expiration attendus ({e})") from None
        options = {c: donnees[c] for c in ("nb_pairs", "anonymat", "note_masquee_avant_relectures", "note_sur",
                                           "seuil_reussite") if c in donnees}
        return cls(tuple(configs.get(e) or ConfigEtape(e, False, 0, Expiration.PASSER) for e in Etape), **options)

    def active(self, etape: Etape) -> bool:
        return any(c.etape == etape and c.active for c in self.etapes)

    def config(self, etape: Etape) -> ConfigEtape:
        for c in self.etapes:
            if c.etape == etape:
                return c
        raise ReglagesInvalides(f"étape « {etape.value} » non configurée")


@dataclass(frozen=True)
class ConfigIA:
    url: str = ""
    modele_texte: str = ""
    modele_code: str = ""
    delai_minutes: int = 10
    seuil_confiance: float = 0.8
    tournures_injection: tuple[str, ...] = TOURNURES_DEFAUT
    plafond_caracteres: int = 60000

    def __post_init__(self):
        if not 0 <= self.seuil_confiance <= 1:
            raise ReglagesInvalides("seuil_confiance doit être compris entre 0 et 1")
        if self.delai_minutes < 0:
            raise ReglagesInvalides("delai_minutes ne peut pas être négatif")
        if self.plafond_caracteres <= 0:
            raise ReglagesInvalides("plafond_caracteres doit être positif")


def _chaine(actives: set[Etape]) -> Chaine:
    delais = {
        Etape.AUTO_EVALUATION: (72, Expiration.PASSER), Etape.CONTROLES: (1, Expiration.PASSER),
        Etape.IA: (1, Expiration.PASSER), Etape.PAIRS: (72, Expiration.REATTRIBUER),
        Etape.JURY: (168, Expiration.ESCALADER), Etape.FORMATEUR: (72, Expiration.ESCALADER),
    }
    return Chaine(tuple(ConfigEtape(e, e in actives, *delais[e]) for e in Etape))


def chaines_defaut() -> dict[TypeExercice, Chaine]:
    base = {Etape.CONTROLES, Etape.IA, Etape.FORMATEUR}
    livrable = base | {Etape.AUTO_EVALUATION, Etape.PAIRS}
    return {
        TypeExercice.MISE_EN_SITUATION: _chaine(base),
        TypeExercice.LIVRABLE: _chaine(livrable),
        TypeExercice.PROJET: _chaine(set(Etape) - {Etape.JURY}),
        TypeExercice.CAPSTONE: _chaine({Etape.CONTROLES, Etape.IA, Etape.JURY, Etape.FORMATEUR}),
    }


CHAINES_DEFAUT: dict[TypeExercice, Chaine] = chaines_defaut()


@dataclass(frozen=True)
class Surcharge:
    cohorte: str | None
    exercice: str | None
    chaine: Chaine
    suppleant: str | None = None  # remplaçant du formateur échu, avant le responsable pédagogique

    def __post_init__(self):
        if self.cohorte is None and self.exercice is None:
            raise ReglagesInvalides("une surcharge doit viser une cohorte ou un exercice")


@dataclass(frozen=True)
class ReglagesEvaluation:
    chaines: dict[TypeExercice, Chaine] = field(default_factory=dict)  # types configurés dans la console
    ia: ConfigIA = field(default_factory=ConfigIA)
    publication_provisoire: bool = False
    responsable_pedagogique: str = ""
    hotes_depots: tuple[str, ...] = ("github.com", "gitlab.com")
    longueur_min_caracteres: int = 200  # contrôle d'une copie texte ; 0 = aucun minimum
    grille_generique: tuple[tuple[str, int], ...] = GRILLE_GENERIQUE_DEFAUT
    niveaux_generiques: tuple[str, ...] = NIVEAUX_GENERIQUES_DEFAUT

    def __post_init__(self):
        for type_, chaine in self.chaines.items():
            self._verifier_publication(chaine, type_)
        if any(poids < 0 for _, poids in self.grille_generique) or sum(p for _, p in self.grille_generique) != 100:
            raise ReglagesInvalides("grille générique : poids positifs totalisant 100")
        if len(self.niveaux_generiques) < 2:
            raise ReglagesInvalides("niveaux génériques : au moins 2 niveaux requis")
        if self.longueur_min_caracteres < 0:
            raise ReglagesInvalides("longueur_min_caracteres ne peut pas être négative")

    def _verifier_publication(self, chaine: Chaine, type_: TypeExercice) -> Chaine:
        if (not self.publication_provisoire
                and chaine.config(Etape.FORMATEUR).expiration == Expiration.PUBLIER_PROVISOIRE):
            raise ReglagesInvalides(
                f"{type_.value} : publication provisoire à l'expiration du formateur non autorisée (option désactivée)")
        return chaine

    def chaine_pour(self, type_: TypeExercice, cohorte: str | None, exercice: str | None,
                    surcharges: tuple[Surcharge, ...], yaml: Chaine | None) -> Chaine:
        """Priorité : surcharge exercice > surcharge cohorte > YAML > type d'exercice > défauts du code."""
        return self._verifier_publication(self._choisir(type_, cohorte, exercice, surcharges, yaml), type_)

    def _choisir(self, type_, cohorte, exercice, surcharges, yaml) -> Chaine:
        for s in surcharges:
            if s.exercice is not None and s.exercice == exercice and s.cohorte in (None, cohorte):
                return s.chaine
        for s in surcharges:
            if s.exercice is None and s.cohorte == cohorte:
                return s.chaine
        if yaml is not None:
            return yaml
        return self.chaines.get(type_) or CHAINES_DEFAUT[type_]
