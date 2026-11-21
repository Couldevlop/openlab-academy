"""Les champs personnalisés posés sur les doctypes du LMS.

Poser un champ est un geste d'infrastructure : il parle à Frappe, pas au métier. Il vivait dans
`entrypoints.install`, ce qui obligeait l'infrastructure à remonter vers la couche d'entrée pour
s'en servir — une dépendance à contresens, et un cycle d'imports qu'il fallait différer à l'appel.
"""
import frappe


def champ_personnalise(doctype: str, nom: str, proprietes: dict) -> None:
    """Crée le champ personnalisé, ou remet ses propriétés à jour s'il existe déjà."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    existant = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": nom})
    if existant:
        champ = frappe.get_doc("Custom Field", existant)
        if any(str(champ.get(k)) != str(v) for k, v in proprietes.items()):
            champ.update(proprietes)
            champ.save(ignore_permissions=True)
    else:
        create_custom_field(doctype, {"fieldname": nom, **proprietes})
