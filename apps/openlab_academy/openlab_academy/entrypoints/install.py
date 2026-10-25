"""Hooks Frappe after_install / after_migrate : réglages, rôles, case « Parcours gratuit », publication des
parcours, cohorte pilote."""
import frappe

from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_evaluation_frappe, reglages_frappe, reglages_source_frappe
from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT

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


ADMINISTRATEUR = "System Manager"
NIVEAU_GRATUIT = 1  # niveau de droits de la case : l'administrateur seul la lit et l'écrit


def preparer_parcours_gratuits() -> None:
    """Case « Parcours gratuit (MOOC) » du formulaire des parcours, en tête de la section des prix, réservée à
    l'administrateur (niveau 1) : ni le créateur du parcours, ni le modérateur, ni l'intendant ne la modifient.
    Propriétés remises à jour sur un site où la case existe déjà."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    from frappe.permissions import setup_custom_perms

    proprietes = {"fieldtype": "Check", "label": "Parcours gratuit (MOOC)", "default": "0",
                  "insert_after": "pricing_section", "permlevel": NIVEAU_GRATUIT,
                  "description": "Aucun paiement : ni tarif, ni échéancier, ni rappel, ni blocage."}
    existant = frappe.db.get_value("Custom Field", {"dt": PARCOURS, "fieldname": CHAMP_GRATUIT})
    if existant:
        champ = frappe.get_doc("Custom Field", existant)
        if any(str(champ.get(k)) != str(v) for k, v in proprietes.items()):
            champ.update(proprietes)
            champ.save(ignore_permissions=True)
    else:
        create_custom_field(PARCOURS, {"fieldname": CHAMP_GRATUIT, **proprietes})
    if not frappe.db.exists("Custom DocPerm", {"parent": PARCOURS, "role": ADMINISTRATEUR,
                                               "permlevel": NIVEAU_GRATUIT}):
        setup_custom_perms(PARCOURS)
        frappe.get_doc({"doctype": "Custom DocPerm", "parent": PARCOURS, "parenttype": "DocType",
                        "parentfield": "permissions", "role": ADMINISTRATEUR, "permlevel": NIVEAU_GRATUIT,
                        "read": 1, "write": 1}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=PARCOURS)


def after_install(commit: bool = True) -> None:
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    preparer_parcours_gratuits()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    cohorte.ouvrir_pilote(commit=commit)


def after_migrate(commit: bool = True) -> None:
    """Republie les parcours à chaque migration : un YAML modifié arrive en base sans commande manuelle."""
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    preparer_parcours_gratuits()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
