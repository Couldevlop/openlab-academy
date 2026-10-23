"""Points d'accroche dans Frappe LMS : ouverture des leçons, verrou des exercices et blocage des parcours impayés
(vérifiés côté serveur)."""
import datetime

import frappe
from frappe.utils import getdate, now_datetime, nowdate
from lms.lms import api as lms_api
from lms.lms import utils as lms_utils
from lms.lms.doctype.course_lesson import course_lesson
from lms.lms.doctype.lms_certificate import lms_certificate
from lms.lms.doctype.lms_quiz import lms_quiz

from openlab_academy.application.acces_exercices import EnregistrerOuverture, VerifierAccesExercices
from openlab_academy.application.acces_parcours import cours_bloques, parcours_bloque, redirection_paiement
from openlab_academy.domain.verrou import ExercicesVerrouilles
from openlab_academy.infrastructure import contenus_parcours_frappe as contenus
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_dossiers_frappe import DOSSIER, DepotDossiersFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import DepotOuverturesFrappe

ROLES_NON_BLOQUES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"}
PREFIXE_CAS = "Mise en situation"
LECTURE = {"read", "select", "print"}
EVALUATIONS = ("LMS Quiz", "LMS Assignment", "LMS Programming Exercise")
CACHE = "openlab_blocages"
TITRE_ERREUR = "Blocage par parcours : calcul impossible"


class ParcoursBloque(frappe.ValidationError):
    """Parcours en retard de paiement : le navigateur reçoit exc_type « ParcoursBloque » et `redirection`."""

    def __init__(self, cours: str):
        self.redirection = redirection_paiement(cours)
        super().__init__("Paiement requis")


# --- blocage par parcours : calculé depuis le dossier (une fois par requête), jamais stocké -----------------
# Fail-safe : une erreur de calcul est journalisée et ne bloque pas (le paiement ne doit pas fermer un parcours
# par accident) ; les règles d'accès du LMS continuent de s'appliquer.
def aujourd_hui() -> datetime.date:
    return getdate(nowdate())


def _cache() -> dict:
    cache = getattr(frappe.local, CACHE, None)
    if cache is None:
        cache = {}
        setattr(frappe.local, CACHE, cache)
    return cache


def vider_cache() -> None:
    setattr(frappe.local, CACHE, {})


def _exempte(utilisateur: str) -> bool:
    return bool(ROLES_NON_BLOQUES & set(frappe.get_roles(utilisateur)))


def _concerne(utilisateur: str | None) -> bool:
    return bool(utilisateur) and utilisateur != "Guest" and not _exempte(utilisateur)


def _journaliser(utilisateur: str, cours: str) -> None:
    """Seulement le nom du dossier et le parcours : jamais l'adresse de l'apprenant ni le détail du dossier."""
    try:
        dossier = frappe.db.get_value(DOSSIER, {"apprenant": utilisateur, "cours": cours}) or "inconnu"
    except Exception:
        dossier = "inconnu"
    frappe.log_error(title=TITRE_ERREUR, message=f"dossier {dossier}, parcours {cours}")


def bloque_pour(utilisateur: str, cours: str | None) -> bool:
    if not cours or not _concerne(utilisateur):
        return False
    cle = (utilisateur, cours, aujourd_hui())
    cache = _cache()
    if cle not in cache:
        try:
            cache[cle] = parcours_bloque(DepotDossiersFrappe(), utilisateur, cours, cle[2])
        except Exception:
            _journaliser(utilisateur, cours)
            return False
    return cache[cle]


def _refuser_si_bloque(cours: str | None, utilisateur: str | None = None) -> None:
    if bloque_pour(utilisateur or frappe.session.user, cours):
        e = ParcoursBloque(cours)
        frappe.local.response["redirection"] = e.redirection
        raise e


def _cours_bloquants(utilisateur: str, doctype: str, nom: str) -> list[str]:
    """Parcours bloqués qui portent l'évaluation, si TOUS ses parcours le sont (sinon aucun) : une évaluation
    partagée reste ouverte tant qu'un de ses parcours l'est."""
    try:
        cours = contenus.cours_de_l_evaluation(doctype, nom)
    except Exception:
        frappe.log_error(title=TITRE_ERREUR, message=f"évaluation {doctype} {nom}")
        return []
    bloques = sorted(c for c in cours if bloque_pour(utilisateur, c))
    return bloques if cours and len(bloques) == len(cours) else []


def _refuser_evaluation_bloquee(utilisateur: str, doctype: str, nom: str) -> None:
    if _concerne(utilisateur) and (bloques := _cours_bloquants(utilisateur, doctype, nom)):
        _refuser_si_bloque(bloques[0], utilisateur)


def lecture_permise(doc, ptype="read", user=None, debug=False):
    """Hook has_permission (leçons, chapitres, évaluations) : refuse la lecture d'un parcours bloqué, sinon sans
    avis (None). Jamais True : Frappe retient le premier avis non nul, un True court-circuiterait les refus du LMS."""
    utilisateur = user or frappe.session.user
    if ptype not in LECTURE or not _concerne(utilisateur):
        return None
    if doc.doctype in EVALUATIONS:
        refuse = bool(_cours_bloquants(utilisateur, doc.doctype, doc.name))
    else:
        refuse = bloque_pour(utilisateur, doc.get("course"))
    return False if refuse else None


def _cours_bloques(utilisateur: str | None) -> tuple[str, ...]:
    if not _concerne(utilisateur):
        return ()
    try:
        return cours_bloques(DepotDossiersFrappe(), utilisateur, aujourd_hui())
    except Exception:
        frappe.log_error(title=TITRE_ERREUR, message="liste des parcours bloqués")
        return ()


def conditions_lecons(user=None, doctype=None) -> str:
    """Listes de leçons (corps compris) : celles des parcours bloqués en sont retirées."""
    return contenus.condition_lecons(_cours_bloques(user or frappe.session.user))


def conditions_quiz(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Quiz", _cours_bloques(user or frappe.session.user), True, True)


def conditions_devoirs(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Assignment", _cours_bloques(user or frappe.session.user), True, False)


def conditions_exercices(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Programming Exercise", _cours_bloques(user or frappe.session.user),
                                          False, False)


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


@frappe.whitelist()
def get_quiz_with_questions(quiz: str) -> dict:
    """Surcharge : questions d'un quiz d'un parcours bloqué jamais servies."""
    _refuser_evaluation_bloquee(frappe.session.user, "LMS Quiz", quiz)
    return lms_utils.get_quiz_with_questions(quiz)


@frappe.whitelist()
def check_answer(quiz: str, question: str, question_type: str, answers: str):
    """Surcharge : bonnes réponses d'un quiz d'un parcours bloqué jamais révélées."""
    _refuser_evaluation_bloquee(frappe.session.user, "LMS Quiz", quiz)
    return lms_quiz.check_answer(quiz, question, question_type, answers)


@frappe.whitelist()
def mark_lesson_progress(course: str, chapter_number: int, lesson_number: int):
    """Surcharge : pas de progression enregistrée sur un parcours bloqué."""
    _refuser_si_bloque(course)
    return lms_api.mark_lesson_progress(course, chapter_number, lesson_number)


@frappe.whitelist()
def save_progress(lesson: str, course: str | None = None, scorm_details: dict = None):
    """Surcharge : idem pour l'enregistrement direct (SCORM) ; le parcours retenu est celui de la leçon."""
    _refuser_si_bloque(contenus.cours_de_la_lecon(lesson))
    return course_lesson.save_progress(lesson, course, scorm_details)


@frappe.whitelist()
def create_certificate(course: str):
    """Surcharge : pas de certificat sur un parcours bloqué, même au contenu achevé."""
    _refuser_si_bloque(course)
    return lms_certificate.create_certificate(course)


def avant_certificat(doc, method=None) -> None:
    """Tout autre chemin de création du certificat : refusé à l'apprenant bloqué ; un membre de l'équipe qui le
    délivre (évaluateur, administrateur) n'est jamais arrêté par le paiement."""
    if _concerne(frappe.session.user):
        _refuser_si_bloque(doc.course, doc.member)


# --- soumissions : parcours bloqué, puis verrou des exercices ----------------------------------------------
def _verifier(apprenant: str, lecon: str | None) -> None:
    if not lecon or ROLES_NON_BLOQUES & set(frappe.get_roles(apprenant)):
        return
    try:
        VerifierAccesExercices(DepotOuverturesFrappe(), reglages_source_frappe.charger(), now_datetime).executer(
            apprenant, lecon)
    except ExercicesVerrouilles as e:
        frappe.throw(str(e), title="Exercices verrouillés")


def avant_soumission_quiz(doc, method=None) -> None:
    _refuser_evaluation_bloquee(doc.member, "LMS Quiz", doc.quiz)
    _verifier(doc.member, frappe.db.get_value("LMS Quiz", doc.quiz, "lesson"))


def avant_soumission_devoir(doc, method=None) -> None:
    _refuser_evaluation_bloquee(doc.member, "LMS Assignment", doc.assignment)
    if not (frappe.db.get_value("LMS Assignment", doc.assignment, "title") or "").startswith(PREFIXE_CAS):
        return
    lecon = frappe.db.get_value("LMS Lesson Assessment", {"assessment_name": doc.assignment}, "parent")
    _verifier(doc.member, lecon)
