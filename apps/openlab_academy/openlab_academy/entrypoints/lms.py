"""Points d'accroche dans Frappe LMS : ouverture des leçons et verrou des exercices (vérifié côté serveur)."""
import frappe
from frappe.utils import now_datetime
from lms.lms import utils as lms_utils

from openlab_academy.application.acces_exercices import EnregistrerOuverture, VerifierAccesExercices
from openlab_academy.domain.verrou import ExercicesVerrouilles
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import DepotOuverturesFrappe

ROLES_NON_BLOQUES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"}
PREFIXE_CAS = "Mise en situation"


@frappe.whitelist(allow_guest=True)
def get_lesson(course: str, chapter: int, lesson: int) -> dict:
    """Surcharge de lms.lms.utils.get_lesson : même réponse, et première ouverture enregistrée."""
    details = lms_utils.get_lesson(course, chapter, lesson)
    utilisateur = frappe.session.user
    if utilisateur != "Guest" and isinstance(details, dict) and details.get("name"):
        EnregistrerOuverture(DepotOuverturesFrappe(), now_datetime).executer(utilisateur, details["name"])
    return details


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
