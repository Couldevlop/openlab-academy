import frappe
from frappe.model.document import Document


class CopieOpenLab(Document):
    pass


def on_doctype_update():
    """Une seule copie par version d'une soumission, même sous rendus concurrents."""
    frappe.db.add_unique("Copie OpenLab", ["soumission", "version"], constraint_name="unique_soumission_version")
