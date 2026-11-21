"""Domaine : un parcours certifiant, ses modules hebdomadaires, son portfolio et son capstone.

Aucune dépendance à Frappe ni au format de stockage.
"""
import math
import re
from dataclasses import dataclass
from enum import Enum

from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages import ReglagesExercices, ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import Chaine

TITRE_MAX = 120  # laisse la place aux préfixes (« Projet 10 — ») sous la limite LMS de 140
_SALAIRE = re.compile(r"\d+\s*k\s*€", re.IGNORECASE)
# Schémas construits (SVG) et photographies d'illustration : une seule extension, en fin de nom,
# pour qu'aucun « photo.jpg.exe » ni aucun chemin ne passe.
_NOM_FIGURE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\.(?:svg|jpg|png|webp)")
# Vidéo d'une séance. Deux formes, et deux seulement.
#   - un chemin dans l'atelier, à la règle de nommage de docs/produire-une-video.md :
#     « <numero>-<parcours>/s<seance>-intro.mp4 » ou « …-demo-<n>.mp4 ». Cette règle décide de toute la
#     chaîne de montage ; un chemin qui s'en écarte publierait un lecteur que la vérification ne saurait
#     pas contrôler. Aucun segment libre, donc aucune remontée (« .. »), aucun chemin absolu, aucun
#     schéma (« javascript: ») : OWASP A01, la valeur vient d'un fichier de parcours.
#   - une adresse complète, en https seulement : une vidéo de cours servie en clair se laisse remplacer
#     en chemin.
_CHEMIN_VIDEO = re.compile(r"\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*/s\d{2}-(?:intro|demo-\d{1,2})\.mp4")
_ADRESSE_VIDEO = re.compile(r"https://[A-Za-z0-9.-]+(?::\d+)?/[A-Za-z0-9._~\-/]*")
# langages colorés par le bloc codeBox du LMS ; au-delà, le bloc s'affiche sans coloration et sans alerte
LANGAGES = frozenset({"python", "json", "yaml", "bash", "sql", "text"})


class ParcoursInvalide(ValueError):
    """Un invariant du parcours n'est pas respecté."""


class Evaluations(str, Enum):
    """Pièces d'évaluation d'une séance.

    Par défaut une séance porte tout : le quiz, la mise en situation et le livrable. Un parcours qui alterne
    un rappel (quiz seul) et une leçon à challenge (livrable seul) choisit séance par séance ; une séance de
    révision ou d'atelier n'évalue rien. Le choix est explicite : un quiz oublié reste une erreur.
    """

    COMPLETES = "completes"
    QUIZ = "quiz"
    LIVRABLE = "livrable"
    AUCUNE = "aucune"

    @property
    def veut_quiz(self) -> bool:
        return self in (Evaluations.COMPLETES, Evaluations.QUIZ)

    @property
    def veut_livrable(self) -> bool:
        return self in (Evaluations.COMPLETES, Evaluations.LIVRABLE)


# comment nommer la séance dans un refus, pour que le message dise ce qui a été déclaré
_SEANCE = {Evaluations.COMPLETES: "séance complète", Evaluations.QUIZ: "séance de quiz seul",
           Evaluations.LIVRABLE: "séance de livrable seul", Evaluations.AUCUNE: "séance sans évaluation"}


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
class Question:
    """Question de quiz de fin de leçon ; les bonnes réponses sont numérotées à partir de 1."""

    enonce: str
    options: tuple[str, ...]
    bonnes: tuple[int, ...]
    explication: str

    def __post_init__(self):
        if not self.enonce.strip():
            raise ParcoursInvalide("question : énoncé manquant")
        if not self.explication.strip():
            raise ParcoursInvalide(f"« {self.enonce[:40]} » : explication manquante")
        if not 2 <= len(self.options) <= 6:
            raise ParcoursInvalide(f"« {self.enonce[:40]} » : 2 à 6 options attendues")
        if any(not o.strip() for o in self.options):
            raise ParcoursInvalide(f"« {self.enonce[:40]} » : option vide")
        if len(set(self.options)) != len(self.options):
            raise ParcoursInvalide(f"« {self.enonce[:40]} » : options en double")
        if not self.bonnes:
            raise ParcoursInvalide(f"« {self.enonce[:40]} » : au moins une bonne réponse")
        for b in self.bonnes:
            if not 1 <= b <= len(self.options):
                raise ParcoursInvalide(
                    f"« {self.enonce[:40]} » : bonne réponse {b} hors des options 1 à {len(self.options)}")

    @property
    def choix_multiple(self) -> bool:
        return len(self.bonnes) > 1


def valider_video(valeur: str) -> str:
    """Vidéo d'une séance : un chemin de l'atelier à la règle de nommage, ou une adresse https.

    Rien d'autre ne passe, et c'est voulu : le chemin désigne un fichier que la vérification de
    publication ira chercher, et la règle de nommage est ce qui permet de le trouver."""
    chemin = (valeur or "").strip()
    if not chemin:
        return ""
    if chemin != valeur:  # un blanc en bord cache une valeur qui ne dit pas ce qu'elle semble dire
        raise ParcoursInvalide(f"vidéo invalide : {valeur!r} (espace ou passage à la ligne en bordure)")
    if _CHEMIN_VIDEO.fullmatch(chemin) or _ADRESSE_VIDEO.fullmatch(chemin):
        return chemin
    raise ParcoursInvalide(
        f"vidéo invalide : {valeur!r} (attendu « 06-ia-agentique/s01-intro.mp4 », "
        "« …/s03-demo-2.mp4 », ou une adresse https complète)")


@dataclass(frozen=True)
class Figure:
    """Illustration d'une leçon : schéma construit par le dépôt, ou photographie livrée avec l'application.
    Le fichier est déposé en fichier privé du site :
    la figure suit donc le contrôle d'accès de la leçon, comme l'archive de départ. Le nom est contraint pour
    qu'aucune valeur de parcours ne puisse désigner un fichier hors du dossier des ressources."""

    nom: str
    legende: str

    def __post_init__(self):
        if not _NOM_FIGURE.fullmatch(self.nom or ""):
            raise ParcoursInvalide(f"nom de figure invalide : {self.nom!r} "
                                   "(attendu « quelque-chose.svg », .jpg, .png ou .webp)")
        if not self.legende.strip():
            raise ParcoursInvalide(f"figure « {self.nom} » : légende obligatoire")


@dataclass(frozen=True)
class Tableau:
    """Tableau de comparaison ou de décision. Le rectangle est vérifié ici : une ligne trop courte produirait
    des cellules vides à l'écran sans que personne ne s'en aperçoive avant la relecture."""

    titre: str
    entetes: tuple[str, ...]
    lignes: tuple[tuple[str, ...], ...]

    def __post_init__(self):
        if not self.entetes:
            raise ParcoursInvalide(f"tableau « {self.titre} » : en-têtes obligatoires")
        if not self.lignes:
            raise ParcoursInvalide(f"tableau « {self.titre} » : au moins une ligne")
        for numero, ligne in enumerate(self.lignes, start=1):
            if len(ligne) != len(self.entetes):
                raise ParcoursInvalide(f"tableau « {self.titre} » : ligne {numero} a {len(ligne)} cellules "
                                       f"pour {len(self.entetes)} colonnes")

    @property
    def largeur(self) -> int:
        return len(self.entetes)


@dataclass(frozen=True)
class Extrait:
    """Extrait de code commenté. Le langage est restreint à ceux que la coloration du LMS connaît : un nom
    fantaisiste donnerait un bloc sans coloration, sans message d'erreur."""

    titre: str
    langage: str
    code: str

    def __post_init__(self):
        if self.langage not in LANGAGES:
            raise ParcoursInvalide(f"extrait « {self.titre} » : langage {self.langage!r} inconnu "
                                   f"({', '.join(sorted(LANGAGES))})")
        if not self.code.strip():
            raise ParcoursInvalide(f"extrait « {self.titre} » : code vide")


@dataclass(frozen=True)
class Section:
    """Une partie du cours d'une séance. Une leçon est un chapitre : elle se lit en sections titrées, chacune
    portant au plus près du texte la figure, le tableau ou l'extrait qui l'explique. Un support posé en fin de
    page n'est plus relié à ce qu'il illustre, et personne ne remonte le lire."""

    titre: str
    paragraphes: tuple[str, ...]
    figures: tuple[Figure, ...] = ()
    tableaux: tuple[Tableau, ...] = ()
    extraits: tuple[Extrait, ...] = ()

    def __post_init__(self):
        if not self.titre.strip():
            raise ParcoursInvalide("section sans titre")
        if not self.paragraphes or not any(p.strip() for p in self.paragraphes):
            raise ParcoursInvalide(f"section « {self.titre} » : au moins un paragraphe")


class AvecCours:
    """Mêlé aux leçons qui portent un chapitre en sections : une séance et le guide de réalisation du projet
    final se lisent de la même façon, donc se rendent et se servent de la même façon."""

    @property
    def toutes_les_figures(self) -> tuple[Figure, ...]:
        """Les figures de la leçon et celles de ses sections, dédoublonnées en conservant l'ordre de lecture."""
        vues: dict[str, Figure] = {}
        for porteur in (self, *self.cours):
            for figure in porteur.figures:
                vues.setdefault(figure.nom, figure)
        return tuple(vues.values())


@dataclass(frozen=True)
class Module(AvecCours):
    num: str
    title: str
    contenu: str
    livrable: str
    quiz: tuple[Question, ...] = ()
    mise_en_situation: str = ""
    evaluations: Evaluations = Evaluations.COMPLETES  # ce que la séance évalue (voir Evaluations)
    travaux_pratiques: str = ""  # support de la séance : déroulé et défi, affiché dans la leçon
    archive: str = ""  # nom de fichier de l'archive de départ, jointe à la leçon et citée par elle
    video: str = ""  # vidéo de la séance : chemin de l'atelier (voir valider_video) ou adresse https
    # l'atelier exécute le code dans le navigateur de l'apprenant : vrai pour les séances de Python seul,
    # faux dès qu'une séance demande un serveur (API, écran, framework web), qui ne peut pas y tourner
    atelier: bool = False
    cours: tuple[Section, ...] = ()  # le chapitre proprement dit, en sections titrées
    figures: tuple[Figure, ...] = ()  # schémas de la séance, servis comme l'archive
    tableaux: tuple[Tableau, ...] = ()
    extraits: tuple[Extrait, ...] = ()
    grille_cas: Grille | None = None  # grille propre à la mise en situation (sinon grille générique)
    correction_cas: Chaine | None = None
    grille_livrable: Grille | None = None
    correction_livrable: Chaine | None = None


    @property
    def veut_quiz(self) -> bool:
        return self.evaluations.veut_quiz

    @property
    def veut_livrable(self) -> bool:
        return self.evaluations.veut_livrable


@dataclass(frozen=True)
class Bloc:
    title: str
    modules: tuple[Module, ...]


@dataclass(frozen=True)
class Projet(AvecCours):
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
    cours: tuple[Section, ...] = ()  # guide de réalisation, en sections titrées
    figures: tuple[Figure, ...] = ()
    tableaux: tuple[Tableau, ...] = ()
    extraits: tuple[Extrait, ...] = ()
    grille: Grille | None = None  # sinon grille dérivée du barème des réglages
    correction: Chaine | None = None

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


def _verifier_textes(objet, champs=("title", "short_introduction", "description")) -> None:
    for champ in champs:
        valeur = getattr(objet, champ)
        if _SALAIRE.search(valeur):
            raise ParcoursInvalide(f"{champ}: rémunération en k€ interdite")
    if not objet.title.strip():
        raise ParcoursInvalide("title manquant")


@dataclass(frozen=True)
class Annonce:
    """Parcours annoncé (« à venir ») : visible au catalogue, sans contenu pédagogique publié."""

    title: str
    short_introduction: str
    description: str
    tags: tuple[str, ...]
    card_gradient: str
    couverture: str = ""  # nom de fichier de l'image de couverture, jointe au parcours et publique

    def __post_init__(self):
        _verifier_textes(self)


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
    couverture: str = ""  # nom de fichier de l'image de couverture, jointe au parcours et publique
    projets_attendus: int = 10
    heures_par_module: int = 8
    questions_par_quiz: int = 0  # 0 = exercices de fin de leçon non exigés
    gratuit: bool = False  # parcours MOOC : aucun tarif ni blocage pour paiement
    acces_limite_a_la_cohorte: bool = False  # ouvert seulement entre les dates de sa cohorte
    mise_en_avant: bool = False  # « featured » du LMS
    # parcours quotidien : une leçon ne s'ouvre qu'une fois la précédente terminée
    progression_sequentielle: bool = False
    # exercices de fin de leçon : valeurs de la plateforme, qu'un parcours peut redéfinir pour ses apprenants
    delai_exercices_minutes: int = 60
    tentatives_max: int = 3
    score_min: int = 100

    def __post_init__(self):
        if self.heures_par_module <= 0:
            raise ParcoursInvalide("heures_par_module doit être positif")
        try:
            self.exercices
        except ReglagesInvalides as e:
            raise ParcoursInvalide(str(e)) from None
        _verifier_textes(self)
        for bloc in self.blocs:
            _titre_court(bloc.title)
            for module in bloc.modules:
                _titre_court(module.title)
        if self.questions_par_quiz:
            self._verifier_exercices()
        nums = [m.num for b in self.blocs for m in b.modules]
        doublons = sorted({n for n in nums if nums.count(n) > 1})
        if doublons:
            raise ParcoursInvalide(f"module '{doublons[0]}' en double")
        if len(self.portfolio) != self.projets_attendus:
            raise ParcoursInvalide(
                f"portfolio: {self.projets_attendus} projets attendus, {len(self.portfolio)} trouvés")
        for i, p in enumerate(self.portfolio):
            if p.apres_module is None:
                raise ParcoursInvalide(f"portfolio[{i}].apres_module manquant")
            if p.apres_module not in nums:
                raise ParcoursInvalide(f"portfolio[{i}].apres_module: module '{p.apres_module}' inexistant")
        if self.capstone.apres_module is not None:
            raise ParcoursInvalide("capstone.apres_module doit être vide")

    @property
    def exercices(self) -> ReglagesExercices:
        """Réglages des exercices appliqués aux leçons de ce parcours."""
        return ReglagesExercices(self.delai_exercices_minutes, self.tentatives_max, self.score_min)

    def _verifier_exercices(self) -> None:
        """Chaque séance porte exactement les pièces qu'elle annonce : ni plus (un rendu que le LMS attendrait
        en vain), ni moins (un quiz oublié)."""
        for module in (m for b in self.blocs for m in b.modules):
            self._verifier_quiz(module)
            self._verifier_livrable(module)
            self._verifier_mise_en_situation(module)

    def _verifier_quiz(self, module: Module) -> None:
        if module.veut_quiz:
            if len(module.quiz) != self.questions_par_quiz:
                raise ParcoursInvalide(f"module {module.num} : {self.questions_par_quiz} questions attendues, "
                                       f"{len(module.quiz)} trouvées")
        elif module.quiz:
            raise ParcoursInvalide(f"module {module.num} : {_SEANCE[module.evaluations]}, mais un quiz est "
                                   "fourni")

    def _verifier_livrable(self, module: Module) -> None:
        if module.veut_livrable:
            if not module.livrable.strip():
                raise ParcoursInvalide(f"module {module.num} : livrable manquant")
        elif module.livrable.strip():
            raise ParcoursInvalide(f"module {module.num} : {_SEANCE[module.evaluations]}, mais un livrable est "
                                   "fourni")

    def _verifier_mise_en_situation(self, module: Module) -> None:
        """La mise en situation accompagne le quiz d'une séance complète ; ailleurs elle n'a personne pour la
        corriger."""
        complete = module.evaluations is Evaluations.COMPLETES
        if complete and not module.mise_en_situation.strip():
            raise ParcoursInvalide(f"module {module.num} : mise en situation manquante")
        if not complete and module.mise_en_situation.strip():
            raise ParcoursInvalide(f"module {module.num} : {_SEANCE[module.evaluations]}, mais une mise en "
                                   "situation est fournie")

    def charge_horaire(self) -> int:
        """Heures de travail apprenant : modules hebdomadaires + portfolio + capstone."""
        modules = sum(len(b.modules) for b in self.blocs) * self.heures_par_module
        return modules + sum(p.duree_h for p in self.portfolio) + self.capstone.duree_h

    def duree_semaines(self, heures_par_semaine: int) -> int:
        if heures_par_semaine <= 0:
            raise ValueError("heures_par_semaine doit être positif")
        return math.ceil(self.charge_horaire() / heures_par_semaine)

    def videos(self) -> tuple[str, ...]:
        """Les vidéos que ce parcours référence, dans l'ordre des séances, sans doublon.

        Ce que la publication doit retrouver sur le serveur avant d'écrire quoi que ce soit."""
        vues: dict[str, None] = {}
        for bloc in self.blocs:
            for module in bloc.modules:
                if module.video:
                    vues.setdefault(module.video)
        return tuple(vues)

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
