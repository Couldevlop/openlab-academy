"""Domaine : réglages de l'évaluation (chaînes d'étapes par type d'exercice, délais, actions à expiration, IA).

Aucune étape ne bloque : chacune a un délai et une action à expiration. Le formateur reste toujours actif,
car seul un humain publie une note définitive.
"""
from dataclasses import dataclass, field
from enum import Enum

from openlab_academy.domain.reglages import ReglagesInvalides

RESERVE_REPONSE_JETONS = 1024  # réponse du modèle (mesurée : moins de 700 jetons pour 4 critères)

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


class Resoumission(str, Enum):
    """Jusqu'à quand un nouveau rendu remplace la copie en cours (au-delà, il est ignoré et l'apprenant prévenu)."""

    ECHEANCE = "echeance"  # jusqu'à l'échéance de l'exercice, même pendant la correction
    DEBUT_CORRECTION = "debut_correction"  # jusqu'au premier geste humain de correction (formateur ou jury)


@dataclass(frozen=True)
class ConfigEtape:
    etape: Etape
    active: bool
    delai_heures: int
    expiration: Expiration


OPTIONS_CHAINE = ("nb_pairs", "anonymat", "note_masquee_avant_relectures", "note_sur", "seuil_reussite",
                  "pairs_attente_max_jours", "pairs_minimum_releves", "pairs_reattributions_max")


@dataclass(frozen=True)
class Chaine:
    etapes: tuple[ConfigEtape, ...]
    nb_pairs: int = 3
    anonymat: bool = True
    note_masquee_avant_relectures: bool = True
    note_sur: int = 20
    seuil_reussite: float = 10.0
    # relecture par les pairs bornée (edX, « flexible peer grading ») : passé ce plafond depuis l'entrée dans
    # l'étape, plus aucune relecture n'est attendue ; la médiane des pairs ne compte qu'à partir du minimum de
    # relectures obtenues ; une copie n'est réattribuée qu'un nombre limité de fois
    pairs_attente_max_jours: int = 7
    pairs_minimum_releves: int = 1
    pairs_reattributions_max: int = 2

    def __post_init__(self):
        if self.nb_pairs < 0:
            raise ReglagesInvalides("nb_pairs ne peut pas être négatif")
        if self.pairs_attente_max_jours < 0:
            raise ReglagesInvalides("pairs_attente_max_jours ne peut pas être négatif")
        if self.pairs_minimum_releves < 0 or (self.nb_pairs and self.pairs_minimum_releves > self.nb_pairs):
            raise ReglagesInvalides("pairs_minimum_releves doit être compris entre 0 et nb_pairs")
        if self.pairs_reattributions_max < 0:
            raise ReglagesInvalides("pairs_reattributions_max ne peut pas être négatif")
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
                "note_sur": self.note_sur, "seuil_reussite": self.seuil_reussite,
                "pairs_attente_max_jours": self.pairs_attente_max_jours,
                "pairs_minimum_releves": self.pairs_minimum_releves,
                "pairs_reattributions_max": self.pairs_reattributions_max}

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
        options = {c: donnees[c] for c in OPTIONS_CHAINE if c in donnees}  # une option inconnue est ignorée
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
    contexte_tokens: int = 4096  # fenêtre du modèle servi, prompt et réponse compris
    citation_min_caracteres: int = 8  # hors blancs : en deçà, un extrait figure dans toute copie

    def __post_init__(self):
        if not 0 <= self.seuil_confiance <= 1:
            raise ReglagesInvalides("seuil_confiance doit être compris entre 0 et 1")
        if self.delai_minutes < 0:
            raise ReglagesInvalides("delai_minutes ne peut pas être négatif")
        if self.plafond_caracteres <= 0:
            raise ReglagesInvalides("plafond_caracteres doit être positif")
        if self.contexte_tokens <= RESERVE_REPONSE_JETONS:
            raise ReglagesInvalides(f"le contexte du modèle doit dépasser {RESERVE_REPONSE_JETONS} jetons "
                                    "(réserve de la réponse)")
        if self.citation_min_caracteres < 1:
            raise ReglagesInvalides("citation_min_caracteres doit être d'au moins 1 (une citation vide ne prouve rien)")


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
    """Réglage ciblé : une chaîne propre, ou seulement un suppléant (la chaîne de la cible reste celle du YAML ou
    du type d'exercice). Le suppléant se règle par cohorte."""

    cohorte: str | None
    exercice: str | None
    chaine: Chaine | None
    suppleant: str | None = None  # remplaçant du formateur échu, avant le responsable pédagogique

    def __post_init__(self):
        if self.cohorte is None and self.exercice is None:
            raise ReglagesInvalides("une surcharge doit viser une cohorte ou un exercice")
        if self.chaine is None and not self.suppleant:
            raise ReglagesInvalides("une surcharge porte une chaîne ou un suppléant")
        if self.exercice is not None and self.suppleant:
            raise ReglagesInvalides("le suppléant du formateur se règle sur la surcharge d'une cohorte, "
                                    "pas d'un exercice")


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
    instantane_fichiers_max: int = 12  # fichiers lus dans un dépôt rendu par lien
    instantane_delai_s: int = 10  # délai de chaque appel à l'hébergeur
    instantane_budget_tache_s: int = 60  # durée totale de l'instantané, pris en tâche de fond
    remise_par_heure: int = 20  # nouveaux rendus par apprenant et par heure ; au-delà, le rendu est refusé (429)
    remise_regroupement_s: int = 30  # rendus rapprochés : seul le dernier est photographié
    resoumission_jusqua: Resoumission = Resoumission.DEBUT_CORRECTION

    def __post_init__(self):
        for type_, chaine in self.chaines.items():
            self._verifier_publication(chaine, type_)
        if any(poids < 0 for _, poids in self.grille_generique) or sum(p for _, p in self.grille_generique) != 100:
            raise ReglagesInvalides("grille générique : poids positifs totalisant 100")
        if len(self.niveaux_generiques) < 2:
            raise ReglagesInvalides("niveaux génériques : au moins 2 niveaux requis")
        if self.longueur_min_caracteres < 0:
            raise ReglagesInvalides("longueur_min_caracteres ne peut pas être négative")
        for champ in ("instantane_fichiers_max", "instantane_delai_s", "instantane_budget_tache_s",
                      "remise_par_heure"):
            if getattr(self, champ) <= 0:
                raise ReglagesInvalides(f"{champ} doit être positif")
        if self.remise_regroupement_s < 0:
            raise ReglagesInvalides("remise_regroupement_s ne peut pas être négatif")

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

    def chaine_effective(self, type_: TypeExercice, cohorte: str | None, exercice: str | None,
                         surcharges: tuple[Surcharge, ...], yaml: Chaine | None) -> tuple[Chaine, bool]:
        """Chaîne à appliquer, et vrai si la chaîne choisie était devenue invalide (par exemple une surcharge
        enregistrée avant la désactivation de la publication provisoire) : rien ne bloque, la chaîne du type
        s'applique."""
        try:
            return self.chaine_pour(type_, cohorte, exercice, surcharges, yaml), False
        except ReglagesInvalides:
            return self.chaine_du_type(type_), True

    def chaine_du_type(self, type_: TypeExercice) -> Chaine:
        return self.chaines.get(type_) or CHAINES_DEFAUT[type_]

    def _choisir(self, type_, cohorte, exercice, surcharges, yaml) -> Chaine:
        avec_chaine = [s for s in surcharges if s.chaine is not None]  # un suppléant seul ne remplace rien
        for s in avec_chaine:
            if s.exercice is not None and s.exercice == exercice and s.cohorte in (None, cohorte):
                return s.chaine
        for s in avec_chaine:
            if s.exercice is None and s.cohorte == cohorte:
                return s.chaine
        if yaml is not None:
            return yaml
        return self.chaine_du_type(type_)
