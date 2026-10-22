"""Page /espace/<chemin> : coquille des écrans d'évaluation (relecture, correcteur, retour), connexion requise.

La page ne porte aucune donnée : les écrans lisent l'API d'évaluation et de paiement, qui contrôle chaque accès côté
serveur. Elle transmet seulement le jeton CSRF de la session, envoyé par les écrans sur chaque écriture, et les droits
qui décident des liens affichés (Intendance, Finances) ; ces droits ne protègent rien : l'API refuse elle-même.
"""
import os
from urllib.parse import urlencode

import frappe

from openlab_academy.entrypoints.paiement_api import ROLES_AGENTS

no_cache = 1
PAQUET = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "espace", "espace.js")


def version() -> str:
    """Empreinte du paquet construit, pour que le navigateur recharge les écrans après une construction."""
    try:
        return str(int(os.path.getmtime(PAQUET)))
    except OSError:
        return "0"


def droits(user: str) -> dict[str, bool]:
    """Écrans des agents : Intendance (intendant, administrateur), Finances (administrateur)."""
    roles = set(frappe.get_roles(user))
    return {"intendance": bool(ROLES_AGENTS & roles), "finances": "System Manager" in roles}


def get_context(context) -> None:
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?" + urlencode({"redirect-to": frappe.local.request.path})
        raise frappe.Redirect
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.version = version()
    context.droits = droits(frappe.session.user)
    frappe.db.commit()  # un jeton CSRF tout juste créé est enregistré dans la session (requête GET)
