"""Hooks Frappe after_install / after_migrate : réglages, publication des parcours, cohorte pilote."""
import frappe

from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_evaluation_frappe, reglages_frappe, reglages_source_frappe

ROLE_INTENDANT = "Intendant OpenLab"
PARCOURS = "LMS Course"


def preparer_roles() -> None:
    """Rôle de l'intendant (suivi des paiements), créé s'il manque, et choix du parcours d'un tarif."""
    if not frappe.db.exists("Role", ROLE_INTENDANT):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE_INTENDANT, "desk_access": 1}).insert(
            ignore_permissions=True)
    _choix_des_parcours()


def _choix_des_parcours() -> None:
    """L'intendant saisit les tarifs : le champ « Parcours » cherche dans LMS Course. Droit « select » seul (liste
    des noms dans un champ lien), sans lecture des parcours ; les droits standard sont d'abord recopiés, Frappe
    n'appliquant plus que les droits personnalisés dès qu'il en existe un."""
    from frappe.permissions import setup_custom_perms

    if frappe.db.exists("Custom DocPerm", {"parent": PARCOURS, "role": ROLE_INTENDANT, "permlevel": 0}):
        return
    setup_custom_perms(PARCOURS)
    frappe.get_doc({"doctype": "Custom DocPerm", "parent": PARCOURS, "parenttype": "DocType",
                    "parentfield": "permissions", "role": ROLE_INTENDANT, "permlevel": 0, "select": 1,
                    "read": 0}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=PARCOURS)


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
