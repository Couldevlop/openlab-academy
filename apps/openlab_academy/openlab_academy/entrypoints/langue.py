"""Langue de l'interface : choix mémorisé sur le compte (connecté) ou dans un cookie (visiteur), traductions du LMS qui
suivent la langue de la requête, langue reprise à la création d'un compte."""
import frappe
from frappe import _
from frappe.translate import get_all_translations

from openlab_academy.domain.langues import DEFAUT, normaliser

COOKIE = "preferred_language"
UN_AN = 365 * 24 * 3600


@frappe.whitelist(allow_guest=True, methods=["POST"])
def choisir(langue: str) -> str:
    """Compte connecté : seul le champ User.language est écrit (sans passer par les permissions du formulaire User).
    Visiteur : cookie d'un an, lu par Frappe côté serveur. Toute valeur hors liste blanche est refusée."""
    retenue = normaliser(langue)
    if retenue is None:
        frappe.throw(_("Langue non prise en charge."), frappe.ValidationError)
    if frappe.session.user == "Guest":
        frappe.local.cookie_manager.set_cookie(COOKIE, retenue, max_age=UN_AN, httponly=True, samesite="Lax")
    else:
        frappe.db.set_value("User", frappe.session.user, "language", retenue, update_modified=False)
    return retenue


@frappe.whitelist(allow_guest=True)
def actuelle() -> str:
    """Langue de la requête en cours (le sélecteur de langue du LMS s'y cale)."""
    return normaliser(frappe.local.lang) or DEFAUT


@frappe.whitelist(allow_guest=True)
def get_translations():
    """Surcharge de lms.lms.api.get_translations, qui lit la langue du Système pour un visiteur : on suit la requête."""
    return get_all_translations(frappe.local.lang)


def initialiser_langue(user, method=None) -> None:
    """Nouveau compte : reprend la langue choisie par le visiteur (cookie) si ce n'est pas le français ; ne touche jamais
    à un compte existant (événement after_insert seulement)."""
    request = getattr(frappe.local, "request", None)
    choisie = normaliser(request.cookies.get(COOKIE)) if request else None
    if choisie and choisie != DEFAUT:
        user.language = choisie
        frappe.db.set_value("User", user.name, "language", choisie, update_modified=False)
