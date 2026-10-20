import frappe
from frappe.model.document import Document


class RelecturePairOpenLab(Document):
    pass


def on_doctype_update():
    """Un pair ne relit jamais deux fois la même copie, même sous attributions concurrentes."""
    frappe.db.add_unique("Relecture Pair OpenLab", ["copie", "relecteur"], constraint_name="unique_copie_relecteur")
