"""Adaptateur : journal non modifiable des actions sur les copies."""
import json

import frappe
from frappe.utils import now_datetime


def journaliser(copie: str, acteur: str, action: str, avant: dict, apres: dict, au_nom_de: str | None = None) -> None:
    frappe.get_doc({
        "doctype": "Journal Note OpenLab", "copie": copie, "acteur": acteur, "au_nom_de": au_nom_de or "",
        "action": action, "horodatage": now_datetime(),
        "avant": json.dumps(avant, ensure_ascii=False, default=str),
        "apres": json.dumps(apres, ensure_ascii=False, default=str),
    }).insert(ignore_permissions=True)
