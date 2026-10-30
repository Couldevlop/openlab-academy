"""Points d'accroche dans Frappe LMS : ouverture des leçons, verrou des exercices et blocage des parcours impayés
(vérifiés côté serveur)."""
import datetime
from urllib.parse import unquote

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate
from lms.lms import api as lms_api
from lms.lms import utils as lms_utils
from lms.lms.doctype.course_lesson import course_lesson
from lms.lms.doctype.lms_certificate import lms_certificate
from lms.lms.doctype.lms_quiz import lms_quiz

from openlab_academy.application.acces_exercices import EnregistrerOuverture, VerifierAccesExercices
from openlab_academy.application.acces_parcours import cours_bloques, parcours_bloque, redirection_paiement
from openlab_academy.application.visibilite import Refus, Visibilite, redirection
from openlab_academy.domain.verrou import ExercicesVerrouilles
from openlab_academy.infrastructure import contenus_parcours_frappe as contenus
from openlab_academy.infrastructure import editorjs
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_dossiers_frappe import DOSSIER, DepotDossiersFrappe
from openlab_academy.infrastructure.depot_ouvertures_frappe import DepotOuverturesFrappe
from openlab_academy.infrastructure.visibilite_frappe import CHAMP_VIDEO, SourceVisibiliteFrappe

ROLES_NON_BLOQUES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"}
PREFIXE_CAS = "Mise en situation"
LECTURE = {"read", "select", "print"}
EVALUATIONS = ("LMS Quiz", "LMS Assignment", "LMS Programming Exercise")
CACHE = "openlab_blocages"
TITRE_ERREUR = "Blocage par parcours : calcul impossible"
TITRE_ERREUR_VISIBILITE = "Visibilité des parcours : calcul impossible"


class ParcoursBloque(frappe.ValidationError):
    """Parcours en retard de paiement : le navigateur reçoit exc_type « ParcoursBloque » et `redirection`."""

    def __init__(self, cours: str):
        self.redirection = redirection_paiement(cours)
        super().__init__("Paiement requis")


class _ParcoursRefuse(frappe.ValidationError):
    """Parcours refusé par la visibilité : le navigateur reçoit exc_type (ParcoursFerme ou ParcoursCache) et
    `redirection`, calculée par le serveur (jamais fournie par le client)."""

    def __init__(self, cours: str, refus: Refus, message: str):
        self.redirection = redirection(refus, cours)
        super().__init__(message)


class ParcoursFerme(_ParcoursRefuse):
    def __init__(self, cours: str):
        super().__init__(cours, Refus.FERME, _("Parcours fermé"))


class ParcoursCache(_ParcoursRefuse):
    def __init__(self, cours: str):
        super().__init__(cours, Refus.CACHE, _("Parcours indisponible"))


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


# --- visibilité (fermeture hors fenêtre, masquage pendant la phase de lancement) : même principe, mais le visiteur
# est concerné et seuls les agents sont exemptés. Erreur de calcul : journalisée, FERME pour un parcours limité
# (fail-safe : la fenêtre ne s'ouvre pas par accident), aucun masquage sinon.
def _source() -> SourceVisibiliteFrappe:
    """Une source par requête : phase, limites et dates lues une fois (vider_cache l'oublie)."""
    cache = _cache()
    if "source" not in cache:
        cache["source"] = SourceVisibiliteFrappe()
    return cache["source"]


def _visibilite() -> Visibilite:
    return Visibilite(_source(), lambda: aujourd_hui())


def refus_pour(utilisateur: str, cours: str | None) -> Refus | None:
    if not cours or not utilisateur:
        return None
    cle = ("refus", utilisateur, cours, aujourd_hui())
    cache = _cache()
    if cle not in cache:
        try:
            cache[cle] = _visibilite().refus(cours, _exempte(utilisateur))
        except Exception:
            frappe.log_error(title=TITRE_ERREUR_VISIBILITE, message=f"parcours {cours}")
            try:
                limite = _source().limite(cours) and not _exempte(utilisateur)
            except Exception:
                limite = False
            cache[cle] = Refus.FERME if limite else None
    return cache[cle]


def _cours_refuses(utilisateur: str | None) -> tuple[str, ...]:
    if not utilisateur:
        return ()
    try:
        return tuple(sorted(_visibilite().refuses(_exempte(utilisateur))))
    except Exception:
        frappe.log_error(title=TITRE_ERREUR_VISIBILITE, message="liste des parcours refusés")
        try:
            return () if _exempte(utilisateur) else tuple(sorted(_source().cours_limites()))
        except Exception:
            return ()


def lot_cache_pour(utilisateur: str, lot: str) -> bool:
    """Cohorte dont tous les parcours sont cachés à cet utilisateur (sa page n'a plus rien à montrer)."""
    try:
        cours = frappe.get_all("Batch Course", {"parent": lot, "parenttype": "LMS Batch"}, pluck="course")
    except Exception:
        frappe.log_error(title=TITRE_ERREUR_VISIBILITE, message=f"cohorte {lot}")
        return False
    return bool(cours) and all(refus_pour(utilisateur, c) is Refus.CACHE for c in cours)


def _lever(refus: Refus, cours: str) -> None:
    e = ParcoursFerme(cours) if refus is Refus.FERME else ParcoursCache(cours)
    frappe.local.response["redirection"] = e.redirection
    raise e


def _refuser(cours: str | None, utilisateur: str | None = None) -> None:
    """Refus de visibilité d'abord (le visiteur y est soumis), puis blocage pour paiement."""
    utilisateur = utilisateur or frappe.session.user
    if refus := refus_pour(utilisateur, cours):
        _lever(refus, cours)
    if bloque_pour(utilisateur, cours):
        e = ParcoursBloque(cours)
        frappe.local.response["redirection"] = e.redirection
        raise e


def refuser_inscription(membre: str, cours: str) -> None:
    """Inscription à un parcours fermé (hors fenêtre) ou caché (phase de lancement) refusée ; les agents ne le sont
    jamais. Le message est traduit dans la langue de la requête."""
    refus = refus_pour(membre, cours)
    if refus is Refus.FERME:
        frappe.throw(_("Les inscriptions à ce parcours sont fermées."), frappe.ValidationError)
    if refus is Refus.CACHE:
        frappe.throw(_("Ce parcours n'est pas disponible pour le moment."), frappe.ValidationError)


def annoncer_cohorte(membre: str, lot: str) -> None:
    """Retient, pour la requête, que l'inscription de ce membre à cette cohorte est en cours d'enregistrement ; posé par
    le crochet de l'inscription à la cohorte, jamais par le client."""
    _cache()[("cohorte_en_cours", membre, lot)] = True


def issue_de_cohorte(doc) -> bool:
    """Inscription au parcours créée par le LMS pendant l'enregistrement d'une inscription à une cohorte qui porte ce
    parcours. Le drapeau `via_batch_enrollment` ne suffit pas (un code ou une entrée mal formée peut le poser) : la
    cohorte doit porter le parcours et son inscription être en cours côté serveur."""
    lot = doc.enrollment_from_batch
    if not (lot and doc.flags.get("via_batch_enrollment")):
        return False
    return bool(_cache().get(("cohorte_en_cours", doc.member, lot))
                and frappe.db.exists("Batch Course", {"parent": lot, "parenttype": "LMS Batch", "course": doc.course}))


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


def _refus_evaluation(utilisateur: str, doctype: str, nom: str) -> tuple[Refus, str] | None:
    """Refus de visibilité d'une évaluation, si TOUS ses parcours sont refusés (une évaluation partagée reste
    ouverte tant qu'un de ses parcours l'est). La fermeture prime sur le masquage, quel que soit l'ordre des
    parcours. Les agents n'y sont jamais soumis."""
    if _exempte(utilisateur):
        return None
    try:
        cours = sorted(contenus.cours_de_l_evaluation(doctype, nom))
    except Exception:
        frappe.log_error(title=TITRE_ERREUR_VISIBILITE, message=f"évaluation {doctype} {nom}")
        return None
    refus = [refus_pour(utilisateur, c) for c in cours]
    if not cours or not all(refus):
        return None
    rang = refus.index(Refus.FERME) if Refus.FERME in refus else 0
    return refus[rang], cours[rang]


def _refuser_evaluation_bloquee(utilisateur: str, doctype: str, nom: str) -> None:
    if refus := _refus_evaluation(utilisateur, doctype, nom):
        _lever(*refus)
    if _concerne(utilisateur) and (bloques := _cours_bloquants(utilisateur, doctype, nom)):
        _refuser(bloques[0], utilisateur)


def lecture_permise(doc, ptype="read", user=None, debug=False):
    """Hook has_permission (leçons, chapitres, évaluations) : refuse la lecture d'un parcours fermé, caché (visiteur
    compris) ou bloqué, sinon sans avis (None). Jamais True : Frappe retient le premier avis non nul, un True
    court-circuiterait les refus du LMS."""
    utilisateur = user or frappe.session.user
    if ptype not in LECTURE or _exempte(utilisateur):
        return None
    if doc.doctype in EVALUATIONS:
        refuse = bool(_refus_evaluation(utilisateur, doc.doctype, doc.name)) or (
            _concerne(utilisateur) and bool(_cours_bloquants(utilisateur, doc.doctype, doc.name)))
    else:
        cours = doc.get("course")
        refuse = bool(refus_pour(utilisateur, cours)) or (_concerne(utilisateur) and bloque_pour(utilisateur, cours))
    return False if refuse else None


def _cours_bloques(utilisateur: str | None) -> tuple[str, ...]:
    if not _concerne(utilisateur):
        return ()
    try:
        return cours_bloques(DepotDossiersFrappe(), utilisateur, aujourd_hui())
    except Exception:
        frappe.log_error(title=TITRE_ERREUR, message="liste des parcours bloqués")
        return ()


def _cours_exclus(utilisateur: str | None) -> tuple[str, ...]:
    """Parcours retirés des listes : bloqués pour paiement, fermés ou cachés."""
    return tuple(sorted(set(_cours_bloques(utilisateur)) | set(_cours_refuses(utilisateur))))


def conditions_lecons(user=None, doctype=None) -> str:
    """Listes de leçons (corps compris) : celles des parcours bloqués, fermés ou cachés en sont retirées."""
    return contenus.condition_lecons(_cours_exclus(user or frappe.session.user))


def conditions_quiz(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Quiz", _cours_exclus(user or frappe.session.user), True, True)


def conditions_devoirs(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Assignment", _cours_exclus(user or frappe.session.user), True, False)


def conditions_exercices(user=None, doctype=None) -> str:
    return contenus.condition_evaluations("LMS Programming Exercise", _cours_exclus(user or frappe.session.user),
                                          False, False)


# --- surcharges des méthodes whitelistées du LMS ----------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_lesson(course: str, chapter: int, lesson: int) -> dict:
    """Surcharge de lms.lms.utils.get_lesson : refus d'un parcours bloqué avant toute lecture, puis même réponse
    et première ouverture enregistrée."""
    _refuser(course)
    details = lms_utils.get_lesson(course, chapter, lesson)
    utilisateur = frappe.session.user
    if utilisateur != "Guest" and isinstance(details, dict) and details.get("name"):
        EnregistrerOuverture(DepotOuverturesFrappe(), now_datetime).executer(utilisateur, details["name"])
    if isinstance(details, dict) and details.get("name"):
        bloc = editorjs.bloc_video(frappe.db.get_value("Course Lesson", details["name"], CHAMP_VIDEO))
        if bloc:  # vidéo en tête du contenu servi, sans écrire en base
            details["content"] = editorjs.avec_video_en_tete(details.get("content"), bloc)
    return details


@frappe.whitelist(allow_guest=True)
def get_course_details(course: str) -> dict:
    """Surcharge : la présentation d'un parcours bloqué, ouverte en naviguant dans l'interface (sans chargement de
    page, donc sans before_request), renvoie elle aussi vers la page de paiement."""
    _refuser(course)
    return lms_utils.get_course_details(course)


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
    _refuser(course)
    return lms_api.mark_lesson_progress(course, chapter_number, lesson_number)


@frappe.whitelist()
def save_progress(lesson: str, course: str | None = None, scorm_details: dict = None):
    """Surcharge : idem pour l'enregistrement direct (SCORM) ; le parcours retenu est celui de la leçon."""
    _refuser(contenus.cours_de_la_lecon(lesson))
    return course_lesson.save_progress(lesson, course, scorm_details)


@frappe.whitelist()
def create_certificate(course: str):
    """Surcharge : pas de certificat sur un parcours bloqué, même au contenu achevé."""
    _refuser(course)
    return lms_certificate.create_certificate(course)


def _refuser_ressource(utilisateur: str, file_url: str) -> None:
    """Fichier privé de leçon : refusé (sans redirection, il se charge comme une image ou une vidéo) si TOUS les
    parcours qui le citent sont refusés ou bloqués ; cité par un parcours ouvert, il reste servi. Fichier cité par
    aucune leçon : le refus appartient au LMS."""
    cours = sorted(contenus.cours_de_la_ressource(unquote(file_url)))
    if cours and all(refus_pour(utilisateur, c) or bloque_pour(utilisateur, c) for c in cours):
        raise frappe.PermissionError


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def serve_resource(file_url: str):
    """Surcharge de lms...course_lesson.serve_resource : un média privé n'est pas servi hors du parcours ouvert
    (fermé, caché ou bloqué pour paiement), même à qui a gardé son adresse ; le LMS applique ensuite ses règles."""
    if isinstance(file_url, str):
        _refuser_ressource(frappe.session.user, file_url)
    return course_lesson.serve_resource(file_url)


def avant_certificat(doc, method=None) -> None:
    """Tout autre chemin de création du certificat : refusé à l'apprenant bloqué ; un membre de l'équipe qui le
    délivre (évaluateur, administrateur) n'est jamais arrêté par le paiement."""
    if _concerne(frappe.session.user):
        _refuser(doc.course, doc.member)


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
