"""Points d'accroche dans Frappe LMS : ouverture des leçons, verrou des exercices et blocage des parcours impayés
(vérifiés côté serveur)."""
import datetime

import frappe
from frappe.utils import getdate, now_datetime, nowdate
from lms.lms import utils as lms_utils
from lms.lms.doctype.lms_quiz import lms_quiz

from openlab_academy.application.acces_exercices import EnregistrerOuverture, VerifierAccesExercices
from openlab_academy.application.acces_parcours import cours_bloques, parcours_bloque, redirection_paiement
from openlab_academy.domain.verrou import ExercicesVerrouilles
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_dossiers_frappe import DepotDossiersFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import DepotOuverturesFrappe

ROLES_NON_BLOQUES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"}
PREFIXE_CAS = "Mise en situation"
LECTURE = {"read", "select", "print"}
EVALUATIONS = ("LMS Quiz", "LMS Assignment", "LMS Programming Exercise")


class ParcoursBloque(frappe.ValidationError):
    """Parcours en retard de paiement : le navigateur reçoit exc_type « ParcoursBloque » et `redirection`."""

    def __init__(self, cours: str):
        self.redirection = redirection_paiement(cours)
        super().__init__("Paiement requis")


# --- blocage par parcours : calculé à chaque requête depuis le dossier, jamais stocké ---------------------
def aujourd_hui() -> datetime.date:
    return getdate(nowdate())


def _exempte(utilisateur: str) -> bool:
    return bool(ROLES_NON_BLOQUES & set(frappe.get_roles(utilisateur)))


def _concerne(utilisateur: str | None) -> bool:
    return bool(utilisateur) and utilisateur != "Guest" and not _exempte(utilisateur)


def bloque_pour(utilisateur: str, cours: str | None) -> bool:
    return bool(cours) and _concerne(utilisateur) and parcours_bloque(
        DepotDossiersFrappe(), utilisateur, cours, aujourd_hui())


def _refuser_si_bloque(cours: str) -> None:
    if bloque_pour(frappe.session.user, cours):
        e = ParcoursBloque(cours)
        frappe.local.response["redirection"] = e.redirection
        raise e


def cours_de_l_evaluation(doctype: str, nom: str) -> set[str]:
    """Parcours qui portent l'évaluation : son champ `course`, la leçon d'un quiz, les leçons qui la placent."""
    lecons = set(frappe.get_all("LMS Lesson Assessment", {"assessment_type": doctype, "assessment_name": nom},
                                pluck="parent"))
    champs = [c for c in ("course", "lesson") if frappe.get_meta(doctype).has_field(c)]
    valeurs = frappe.db.get_value(doctype, nom, champs, as_dict=True) if champs else None
    cours = {valeurs.get("course")} if valeurs else set()
    if valeurs and valeurs.get("lesson"):
        lecons.add(valeurs.lesson)
    if lecons:
        cours |= set(frappe.get_all("Course Lesson", {"name": ["in", list(lecons)]}, pluck="course"))
    return {c for c in cours if c}


def _evaluation_bloquee(utilisateur: str, doctype: str, nom: str) -> bool:
    """Bloquée dès qu'un parcours qui la porte est bloqué (une évaluation partagée suit le plus strict)."""
    return any(bloque_pour(utilisateur, c) for c in cours_de_l_evaluation(doctype, nom))


def lecture_permise(doc, ptype="read", user=None, debug=False):
    """Hook has_permission (leçons, chapitres, évaluations) : refuse la lecture d'un parcours bloqué, sinon sans
    avis (None) pour laisser décider les règles du LMS — un True accorderait l'accès à leur place."""
    utilisateur = user or frappe.session.user
    if ptype not in LECTURE or not _concerne(utilisateur):
        return None
    if doc.doctype in EVALUATIONS:
        refuse = _evaluation_bloquee(utilisateur, doc.doctype, doc.name)
    else:
        refuse = bloque_pour(utilisateur, doc.get("course"))
    return False if refuse else None


def _cours_bloques(utilisateur: str | None) -> tuple[str, ...]:
    if not _concerne(utilisateur):
        return ()
    return cours_bloques(DepotDossiersFrappe(), utilisateur, aujourd_hui())


def _liste(cours: tuple[str, ...]) -> str:
    return ", ".join(frappe.db.escape(c) for c in cours)


def conditions_lecons(user=None, doctype=None) -> str:
    """Listes de leçons (corps compris) : celles des parcours bloqués en sont retirées."""
    cours = _cours_bloques(user or frappe.session.user)
    return f"ifnull(`tabCourse Lesson`.course, '') not in ({_liste(cours)})" if cours else ""


def _conditions_evaluations(doctype: str, user, champ_cours: bool, champ_lecon: bool) -> str:
    cours = _cours_bloques(user or frappe.session.user)
    if not cours:
        return ""
    liste = _liste(cours)
    conditions = [
        f"`tab{doctype}`.name not in (select la.assessment_name from `tabLMS Lesson Assessment` la"
        f" inner join `tabCourse Lesson` cl on cl.name = la.parent"
        f" where la.assessment_type = {frappe.db.escape(doctype)} and cl.course in ({liste}))"]
    if champ_cours:
        conditions.append(f"ifnull(`tab{doctype}`.course, '') not in ({liste})")
    if champ_lecon:
        conditions.append(f"ifnull(`tab{doctype}`.lesson, '') not in"
                          f" (select cl.name from `tabCourse Lesson` cl where cl.course in ({liste}))")
    return " and ".join(conditions)


def conditions_quiz(user=None, doctype=None) -> str:
    return _conditions_evaluations("LMS Quiz", user, champ_cours=True, champ_lecon=True)


def conditions_devoirs(user=None, doctype=None) -> str:
    return _conditions_evaluations("LMS Assignment", user, champ_cours=True, champ_lecon=False)


def conditions_exercices(user=None, doctype=None) -> str:
    return _conditions_evaluations("LMS Programming Exercise", user, champ_cours=False, champ_lecon=False)


# --- surcharges des méthodes whitelistées du LMS ----------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_lesson(course: str, chapter: int, lesson: int) -> dict:
    """Surcharge de lms.lms.utils.get_lesson : refus d'un parcours bloqué avant toute lecture, puis même réponse
    et première ouverture enregistrée."""
    _refuser_si_bloque(course)
    details = lms_utils.get_lesson(course, chapter, lesson)
    utilisateur = frappe.session.user
    if utilisateur != "Guest" and isinstance(details, dict) and details.get("name"):
        EnregistrerOuverture(DepotOuverturesFrappe(), now_datetime).executer(utilisateur, details["name"])
    return details


def _refuser_evaluation_bloquee(doctype: str, nom: str) -> None:
    utilisateur = frappe.session.user
    if not _concerne(utilisateur):
        return
    for cours in sorted(cours_de_l_evaluation(doctype, nom)):
        _refuser_si_bloque(cours)


@frappe.whitelist()
def get_quiz_with_questions(quiz: str) -> dict:
    """Surcharge : questions d'un quiz d'un parcours bloqué jamais servies."""
    _refuser_evaluation_bloquee("LMS Quiz", quiz)
    return lms_utils.get_quiz_with_questions(quiz)


@frappe.whitelist()
def check_answer(quiz: str, question: str, question_type: str, answers: str):
    """Surcharge : bonnes réponses d'un quiz d'un parcours bloqué jamais révélées."""
    _refuser_evaluation_bloquee("LMS Quiz", quiz)
    return lms_quiz.check_answer(quiz, question, question_type, answers)


# --- verrou des exercices -------------------------------------------------------------------------------
def _verifier(apprenant: str, lecon: str | None) -> None:
    if not lecon or ROLES_NON_BLOQUES & set(frappe.get_roles(apprenant)):
        return
    try:
        VerifierAccesExercices(DepotOuverturesFrappe(), reglages_source_frappe.charger(), now_datetime).executer(
            apprenant, lecon)
    except ExercicesVerrouilles as e:
        frappe.throw(str(e), title="Exercices verrouillés")


def avant_soumission_quiz(doc, method=None) -> None:
    _verifier(doc.member, frappe.db.get_value("LMS Quiz", doc.quiz, "lesson"))


def avant_soumission_devoir(doc, method=None) -> None:
    if not (frappe.db.get_value("LMS Assignment", doc.assignment, "title") or "").startswith(PREFIXE_CAS):
        return
    lecon = frappe.db.get_value("LMS Lesson Assessment", {"assessment_name": doc.assignment}, "parent")
    _verifier(doc.member, lecon)
