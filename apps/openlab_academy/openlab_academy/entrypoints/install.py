"""Hooks Frappe after_install / after_migrate : réglages, publication des parcours, cohorte pilote."""
import frappe

from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_evaluation_frappe, reglages_frappe, reglages_source_frappe

ROLE_INTENDANT = "Intendant OpenLab"


def preparer_roles() -> None:
    """Rôle de l'intendant (suivi des paiements), créé s'il manque."""
    if not frappe.db.exists("Role", ROLE_INTENDANT):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE_INTENDANT, "desk_access": 1}).insert(
            ignore_permissions=True)


def after_install(commit: bool = True) -> None:
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    cohorte.ouvrir_pilote(commit=commit)


def after_migrate(commit: bool = True) -> None:
    """Republie les parcours à chaque migration : un YAML modifié arrive en base sans commande manuelle."""
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    seed.run(commit=commit)
