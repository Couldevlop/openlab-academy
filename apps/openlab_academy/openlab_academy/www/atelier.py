"""Page /atelier?lecon=<leçon> : l'atelier de code, connexion requise.

La page ne porte aucune donnée du dépôt : l'atelier les demande à l'API, qui contrôle l'accès leçon
par leçon. Elle transmet le nom de la leçon demandée et le jeton CSRF de la session.
"""
import os

import frappe

no_cache = 1
PAQUET = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "atelier", "atelier.js")


def version() -> str:
    """Empreinte du fichier servi, pour que le navigateur recharge l'atelier après une mise à jour."""
    try:
        return str(int(os.path.getmtime(PAQUET)))
    except OSError:
        return "0"


def get_context(context):
    """Exige une session ouverte, puis passe la leçon demandée à l'atelier."""
    if frappe.session.user == "Guest":
        frappe.throw(frappe._("Connectez-vous pour ouvrir l'atelier."), frappe.PermissionError)
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.lecon = frappe.form_dict.get("lecon") or ""
    context.version = version()
    return context
