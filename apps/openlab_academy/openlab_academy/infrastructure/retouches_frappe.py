"""Retouches faites dans l'application : marquées à l'enregistrement, conservées à la republication.

Un parcours naît d'un fichier, mais rien n'empêche de le retoucher dans l'application : l'éditeur du
LMS ouvre le contenu des séances, les énoncés de challenge, les questions de quiz et la fiche du
parcours. Le problème est le retour du fichier, qui réécrit tout à chaque migration. D'où la case
portée ici : posée dès qu'une pièce change hors publication, elle met la republication en retrait pour
cette pièce seule. Décochée par un administrateur, le fichier reprend la main à la publication
suivante.

Quatre pièces sont protégées, chacune avec sa clé d'appariement, puisque la republication détruit puis
recrée les documents :

- la séance (`Course Lesson`), par son titre ;
- le challenge et son corrigé (`LMS Assignment`), par son titre ;
- la question de quiz (`LMS Question`), par le titre de son quiz et son rang ;
- la fiche du parcours (`LMS Course`), qui ne bouge pas et se reconnaît elle-même.

Le contenu conservé d'une séance cite le quiz et les devoirs par leur identifiant, et la republication
les recrée : les anciens identifiants y sont donc remplacés par les nouveaux, appariés par titre.
"""
import contextlib

import frappe

CHAMP = "contenu_modifie_en_ligne"  # Check : la republication laisse cette pièce en place
DRAPEAU = "openlab_publication_en_cours"  # posé le temps d'une publication : ses écritures ne marquent rien

LECON = "Course Lesson"
DEVOIR = "LMS Assignment"
QUESTION = "LMS Question"
PARCOURS = "LMS Course"
QUIZ = "LMS Quiz"
EXERCICES = (QUIZ, DEVOIR)

_OPTIONS = tuple(f"option_{i}" for i in range(1, 11))
_EXPLICATIONS = tuple(f"explanation_{i}" for i in range(1, 11))
_BONNES = tuple(f"is_correct_{i}" for i in range(1, 11))

# Les champs qu'une retouche peut toucher, par doctype : ce sont eux qu'on surveille et qu'on reconduit.
SUIVIS = {
    LECON: ("content",),
    DEVOIR: ("question", "answer"),
    QUESTION: ("question", "multiple", *_OPTIONS, *_EXPLICATIONS, *_BONNES),
    PARCOURS: ("title", "short_introduction", "description", "tags"),
}


@contextlib.contextmanager
def publication():
    """Le temps d'une publication, les écritures de l'application ne marquent aucune pièce."""
    precedent = frappe.flags.get(DRAPEAU)
    frappe.flags[DRAPEAU] = True
    try:
        yield
    finally:
        frappe.flags[DRAPEAU] = precedent


def retouche(doc, methode=None) -> None:
    """Hook on_update : marque la pièce dont un champ suivi vient de changer hors publication."""
    champs = SUIVIS.get(doc.doctype)
    if not champs or frappe.flags.get(DRAPEAU) or doc.get(CHAMP):
        return
    avant = doc.get_doc_before_save()
    if avant is None or all(_egal(avant.get(champ), doc.get(champ)) for champ in champs):
        return
    frappe.db.set_value(doc.doctype, doc.name, CHAMP, 1, update_modified=False)


def _egal(avant, apres) -> bool:
    """Une case vide revient tantôt en 0, tantôt en None : la comparaison brute crierait au changement."""
    return (avant or "") == (apres or "")


def _valeurs(doctype: str, nom: str) -> dict:
    champs = SUIVIS[doctype]
    return frappe.db.get_value(doctype, nom, champs, as_dict=True) or {}


class Retouches:
    """Ce qu'un parcours porte de retouché, relevé avant que la republication ne détruise ses documents."""

    def __init__(self, parcours: dict, lecons: dict, devoirs: dict, questions: dict):
        self.parcours = parcours  # {champ: valeur} ou {} si la fiche n'a pas été retouchée
        self.lecons = lecons      # {titre de leçon: contenu}
        self.devoirs = devoirs    # {titre de devoir: {champ: valeur}}
        self.questions = questions  # {(titre de quiz, rang): {champ: valeur}}

    def __bool__(self) -> bool:
        return bool(self.parcours or self.lecons or self.devoirs or self.questions)


def relever(cours_id: str) -> Retouches:
    """Toutes les retouches du parcours, avec de quoi les reposer sur les documents recréés."""
    return Retouches(parcours=_parcours_retouche(cours_id), lecons=_lecons(cours_id),
                     devoirs=_devoirs(cours_id), questions=_questions(cours_id))


def _parcours_retouche(cours_id: str) -> dict:
    if not frappe.db.get_value(PARCOURS, cours_id, CHAMP):
        return {}
    return _valeurs(PARCOURS, cours_id)


def _lecons(cours_id: str) -> dict[str, str]:
    lecons = frappe.get_all(LECON, {"course": cours_id, CHAMP: 1}, ["title", "content"])
    return {l.title: l.content for l in lecons if l.content}


def _devoirs(cours_id: str) -> dict[str, dict]:
    devoirs = frappe.get_all(DEVOIR, {"course": cours_id, CHAMP: 1}, ["name", "title"])
    return {d.title: _valeurs(DEVOIR, d.name) for d in devoirs}


def _rangs(quiz: str) -> list[str]:
    return frappe.get_all("LMS Quiz Question", {"parent": quiz}, pluck="question", order_by="idx")


def _questions(cours_id: str) -> dict[tuple[str, int], dict]:
    retouchees = {}
    for quiz in frappe.get_all(QUIZ, {"course": cours_id}, ["name", "title"]):
        for rang, question in enumerate(_rangs(quiz.name)):
            if frappe.db.get_value(QUESTION, question, CHAMP):
                retouchees[(quiz.title, rang)] = _valeurs(QUESTION, question)
    return retouchees


def exercices(cours_id: str) -> dict[str, str]:
    """{identifiant d'exercice: titre} du parcours : la clé d'appariement d'une republication est le titre."""
    return {e.name: e.title
            for doctype in EXERCICES
            for e in frappe.get_all(doctype, {"course": cours_id}, ["name", "title"])}


def champs_du_parcours(cours_id: str, champs: dict) -> dict:
    """Retire de ce que la publication écrirait les champs de fiche retouchés dans l'application."""
    if not frappe.db.get_value(PARCOURS, cours_id, CHAMP):
        return champs
    return {cle: valeur for cle, valeur in champs.items() if cle not in SUIVIS[PARCOURS]}


def reconduire(cours_id: str, retouches: Retouches, anciens: dict[str, str]) -> None:
    """Repose les retouches sur les documents que la republication vient de recréer."""
    if not retouches:
        return
    nouveaux = {titre: nom for nom, titre in exercices(cours_id).items()}
    remplacements = {ancien: nouveaux[titre] for ancien, titre in anciens.items()
                     if titre in nouveaux and nouveaux[titre] != ancien}
    _reposer_lecons(cours_id, retouches.lecons, remplacements)
    _reposer_devoirs(cours_id, retouches.devoirs)
    _reposer_questions(cours_id, retouches.questions)


def _reposer_lecons(cours_id: str, contenus: dict[str, str], remplacements: dict[str, str]) -> None:
    for titre, contenu in contenus.items():
        nom = frappe.db.get_value(LECON, {"course": cours_id, "title": titre})
        if not nom:  # la séance a disparu du fichier de parcours : rien à reconduire
            continue
        for ancien, nouveau in remplacements.items():
            contenu = contenu.replace(ancien, nouveau)
        frappe.db.set_value(LECON, nom, {"content": contenu, CHAMP: 1})


def _reposer_devoirs(cours_id: str, devoirs: dict[str, dict]) -> None:
    for titre, valeurs in devoirs.items():
        nom = frappe.db.get_value(DEVOIR, {"course": cours_id, "title": titre})
        if nom:
            frappe.db.set_value(DEVOIR, nom, {**valeurs, CHAMP: 1})


def _reposer_questions(cours_id: str, questions: dict[tuple[str, int], dict]) -> None:
    if not questions:
        return
    rangs = {(quiz.title, rang): question
             for quiz in frappe.get_all(QUIZ, {"course": cours_id}, ["name", "title"])
             for rang, question in enumerate(_rangs(quiz.name))}
    for cle, valeurs in questions.items():
        nom = rangs.get(cle)
        if nom:  # le quiz a pu raccourcir entre deux versions du fichier
            frappe.db.set_value(QUESTION, nom, {**valeurs, CHAMP: 1})
