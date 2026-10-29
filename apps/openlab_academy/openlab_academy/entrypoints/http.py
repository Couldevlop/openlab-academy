"""Hooks HTTP Frappe : habillage des pages HTML de l'interface /lms et stockage du navigateur vidé à la connexion et
à la déconnexion (after_request) ; redirection d'un parcours en retard de paiement vers sa page de paiement
(before_request, chargement complet d'une page) ; langue de la requête restreinte à fr/en (before_request)."""
import re

import frappe
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from openlab_academy.application.acces_parcours import redirection_paiement
from openlab_academy.domain.langues import resoudre
from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.habillage import injecter

# pages d'un parcours dans l'interface LMS : /lms/courses/<cours>[/learn/…|/chapter/…|/certification|…]
PAGE_DE_PARCOURS = re.compile(r"^/lms/courses/([^/]+)(?:/|$)")
PAS_UN_PARCOURS = {"new", "import"}  # écrans de création du LMS sous le même préfixe
# le LMS garde ses documents dans le stockage du navigateur (IndexedDB), sans distinguer les utilisateurs : sur un poste
# partagé, l'apprenant suivant verrait le rendu du précédent
CHANGEMENT_D_UTILISATEUR = {"/api/method/login", "/api/method/logout"}


def _est_page_lms(chemin: str) -> bool:
    return chemin == "/lms" or chemin.startswith("/lms/")


def after_request(response, request) -> None:
    if response is None:  # before_request a répondu (redirection) : rien à habiller
        return
    if request.path in CHANGEMENT_D_UTILISATEUR or request.args.get("cmd") == "web_logout":
        response.headers["Clear-Site-Data"] = '"storage"'
    if response.direct_passthrough or response.mimetype != "text/html" or not _est_page_lms(request.path):
        return
    response.set_data(injecter(response.get_data(as_text=True)))


def _parcours_demande(request) -> str | None:
    """Parcours d'une page HTML demandée en GET ; None pour tout le reste (API, fichiers, /espace, /login…)."""
    if request.method != "GET" or "text/html" not in (request.headers.get("Accept") or ""):
        return None
    trouve = PAGE_DE_PARCOURS.match(request.path)
    if not trouve or trouve.group(1) in PAS_UN_PARCOURS:
        return None
    return trouve.group(1)


def _fixer_langue(request) -> None:
    """Frappe a déjà résolu frappe.local.lang (HTTPRequest.set_lang, avant les hooks before_request) en suivant _lang,
    le compte, le cookie puis Accept-Language : on ramène le résultat à fr/en, sans jamais suivre Accept-Language."""
    connecte = frappe.session.user != "Guest"
    frappe.local.lang = resoudre(
        frappe.form_dict.get("_lang"), request.cookies.get("preferred_language"),
        frappe.get_cached_value("User", frappe.session.user, "language") if connecte else None,
        connecte, frappe.local.lang)


def before_request() -> None:
    """Langue ramenée à fr/en ; page d'un parcours bloqué → 302 vers /espace/paiement/<cours>. Aucune lecture en base hors de ces pages.
    Frappe renvoie telle quelle une HTTPException levée ici (frappe.Redirect n'y est pas géré)."""
    _fixer_langue(frappe.local.request)
    cours = _parcours_demande(frappe.local.request)
    if cours and lms.bloque_pour(frappe.session.user, cours):
        abort(redirect(redirection_paiement(cours), 302))
