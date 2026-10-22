"""Hooks HTTP Frappe : habillage des pages HTML de l'interface /lms (after_request) et redirection d'un parcours
en retard de paiement vers sa page de paiement (before_request, chargement complet d'une page)."""
import re

import frappe
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.habillage import injecter

# pages d'un parcours dans l'interface LMS : /lms/courses/<cours>[/learn/…|/chapter/…|/certification|…]
PAGE_DE_PARCOURS = re.compile(r"^/lms/courses/([^/]+)(?:/|$)")
PAS_UN_PARCOURS = {"new", "import"}  # écrans de création du LMS sous le même préfixe


def _est_page_lms(chemin: str) -> bool:
    return chemin == "/lms" or chemin.startswith("/lms/")


def after_request(response, request) -> None:
    if response is None:  # before_request a répondu (redirection) : rien à habiller
        return
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


def before_request() -> None:
    """Page d'un parcours bloqué → 302 vers /espace/paiement/<cours>. Aucune lecture en base hors de ces pages.
    Frappe renvoie telle quelle une HTTPException levée ici (frappe.Redirect n'y est pas géré)."""
    cours = _parcours_demande(frappe.local.request)
    if cours and lms.bloque_pour(frappe.session.user, cours):
        abort(redirect(lms.redirection_paiement(cours), 302))
