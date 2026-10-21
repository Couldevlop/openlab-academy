"""Domaine : réglages de l'évaluation (chaînes d'étapes par type d'exercice, délais, actions à expiration, IA).

Aucune étape ne bloque : chacune a un délai et une action à expiration. Le formateur reste toujours actif,
car seul un humain publie une note définitive.
"""
from collections.abc import Callable
from dataclasses import dataclass, field, replace
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
    """Réglage partiel ciblé (cohorte, exercice, ou exercice dans une cohorte) : un champ absent est hérité, une
    étape citée ne remplace que la configuration de cette étape. L'équipe de correction (titulaires, suppléants,
    responsable) se règle à part (domain.equipe)."""

    cohorte: str | None
    exercice: str | None
    options: dict = field(default_factory=dict)  # sous-ensemble de OPTIONS_CHAINE
    etapes: tuple[ConfigEtape, ...] = ()

    def __post_init__(self):
        if self.cohorte is None and self.exercice is None:
            raise ReglagesInvalides("une surcharge doit viser une cohorte ou un exercice")
        if not (self.options or self.etapes):
            raise ReglagesInvalides("une surcharge porte au moins un réglage")
        inconnues = sorted(set(self.options) - set(OPTIONS_CHAINE))
        if inconnues:
            raise ReglagesInvalides(f"réglage de chaîne inconnu : {', '.join(inconnues)}")

    @classmethod
    def complete(cls, cohorte: str | None, exercice: str | None, chaine: Chaine) -> "Surcharge":
        """Surcharge qui fixe tous les champs d'une chaîne (forme des surcharges d'avant les surcharges
        partielles)."""
        return cls(cohorte, exercice, {c: getattr(chaine, c) for c in OPTIONS_CHAINE}, chaine.etapes)

    @property
    def libelle(self) -> str:
        if self.exercice and self.cohorte:
            return f"exercice {self.exercice} / cohorte {self.cohorte}"
        return f"exercice {self.exercice}" if self.exercice else f"cohorte {self.cohorte}"

    def appliquer(self, chaine: Chaine) -> Chaine:
        """La chaîne obtenue est revalidée : une fusion incohérente est refusée."""
        etapes = {c.etape: c for c in chaine.etapes} | {c.etape: c for c in self.etapes}
        return replace(chaine, etapes=tuple(etapes[e] for e in Etape if e in etapes), **self.options)


def surcharges_applicables(surcharges, cohorte: str | None, exercice: str | None) -> list[Surcharge]:
    """Dans l'ordre d'application : cohorte, puis exercice, puis exercice dans cette cohorte (le plus spécifique
    l'emporte, champ par champ)."""
    rang = []
    for s in surcharges:
        if s.exercice is None and s.cohorte is not None and s.cohorte == cohorte:
            rang.append((0, s))
        elif s.exercice is not None and s.exercice == exercice and s.cohorte in (None, cohorte):
            rang.append((1 if s.cohorte is None else 2, s))
    return [s for _, s in sorted(rang, key=lambda r: r[0])]


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
        """Priorité, champ par champ : surcharge exercice > surcharge cohorte > YAML > type d'exercice > défauts
        du code."""
        chaine = yaml if yaml is not None else self.chaine_du_type(type_)
        for s in surcharges_applicables(surcharges, cohorte, exercice):
            chaine = s.appliquer(chaine)
        return self._verifier_publication(chaine, type_)

    def resoudre_reglages(self, type_: TypeExercice, cohorte: str | None, exercice: str | None,
                          surcharges: tuple[Surcharge, ...], yaml: Chaine | None) -> dict[str, dict]:
        """Valeur effective et provenance de chaque champ de la chaîne : {champ: {valeur, source}}."""
        if yaml is not None:
            base, source = yaml, "YAML de l'exercice"
        else:
            base, source = self.chaine_du_type(type_), f"type {type_.value}" if type_ in self.chaines else "défauts"
        resolu = {c: {"valeur": getattr(base, c), "source": source} for c in OPTIONS_CHAINE}
        resolu |= {f"etape.{c.etape.value}": {"valeur": _config_dict(c), "source": source} for c in base.etapes}
        for s in surcharges_applicables(surcharges, cohorte, exercice):
            resolu |= {c: {"valeur": v, "source": s.libelle} for c, v in s.options.items()}
            resolu |= {f"etape.{c.etape.value}": {"valeur": _config_dict(c), "source": s.libelle} for c in s.etapes}
        return resolu

    def chaine_effective(self, type_: TypeExercice, cohorte: str | None, exercice: str | None,
                         surcharges: tuple[Surcharge, ...], yaml: Chaine | None) -> tuple[Chaine, str | None]:
        """Chaîne à appliquer, et la cause si la chaîne choisie était devenue invalide (par exemple une surcharge
        enregistrée avant la désactivation de la publication provisoire) : rien ne bloque, la copie part sur la
        chaîne de secours."""
        try:
            return self.chaine_pour(type_, cohorte, exercice, surcharges, yaml), None
        except ReglagesInvalides as e:
            return self.chaine_de_secours(type_), str(e)

    def chaine_de_secours(self, type_: TypeExercice) -> Chaine:
        """Le formateur seul, avec son délai pour ce type et l'escalade à l'expiration (jamais de publication
        provisoire) ; barème, seuil et options du type gardés."""
        base = self.chaine_du_type(type_)
        formateur = base.config(Etape.FORMATEUR)
        return replace(base, etapes=tuple(
            ConfigEtape(c.etape, True, formateur.delai_heures, Expiration.ESCALADER) if c.etape == Etape.FORMATEUR
            else replace(c, active=False) for c in base.etapes))

    def chaine_du_type(self, type_: TypeExercice) -> Chaine:
        return self.chaines.get(type_) or CHAINES_DEFAUT[type_]


def _config_dict(c: ConfigEtape) -> dict:
    return {"active": c.active, "delai_heures": c.delai_heures, "expiration": c.expiration.value}


def surcharges_invalidees(reglages: ReglagesEvaluation, surcharges: tuple[Surcharge, ...],
                          exercices: Callable[[str], tuple[TypeExercice, Chaine | None] | None],
                          impliquant: Surcharge | None = None) -> list[tuple[str, str]]:
    """Cibles (cohorte, exercice) atteintes par les surcharges dont la chaîne fusionnée serait invalide, avec le
    motif. Chaque cohorte surchargée est croisée avec chaque exercice surchargé ; un exercice connu est vérifié
    avec son type et son YAML, une cohorte (ou un exercice inconnu) avec chaque type. Une combinaison n'est pas
    signalée quand une partie plus petite l'est déjà. Avec `impliquant`, seules les cibles qu'il atteint."""
    cohortes = sorted({s.cohorte for s in surcharges if s.cohorte is not None})
    exos = sorted({s.exercice for s in surcharges if s.exercice is not None})
    cibles = [(c, None) for c in cohortes] + [(None, x) for x in exos] + [(c, x) for c in cohortes for x in exos]
    contextes = []
    for cohorte, exercice in cibles:
        indices = [i for i, s in enumerate(surcharges) if s in surcharges_applicables((s,), cohorte, exercice)]
        if indices:
            contextes.append((cohorte, exercice, frozenset(indices)))
    fautives: list[tuple[frozenset, str, str]] = []
    for cohorte, exercice, indices in sorted(contextes, key=lambda c: len(c[2])):
        if any(f <= indices for f, _, _ in fautives):
            continue
        connu = exercices(exercice) if exercice else None
        essais = [connu] if connu else [(t, None) for t in TypeExercice]
        for type_, yaml in essais:
            try:
                reglages.chaine_pour(type_, cohorte, exercice, surcharges, yaml)
            except ReglagesInvalides as e:
                libelle = " + ".join(s.libelle for s in surcharges_applicables(surcharges, cohorte, exercice))
                fautives.append((indices, libelle, str(e)))
                break
    return [(libelle, motif) for indices, libelle, motif in fautives
            if impliquant is None or any(surcharges[i] == impliquant for i in indices)]
