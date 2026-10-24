"""Adaptateur : journal non modifiable des actions sur les dossiers de paiement."""
import json

import frappe
from frappe.utils import now_datetime


def journaliser(dossier: str, acteur: str, action: str, avant: dict, apres: dict, motif: str = "") -> None:
    frappe.get_doc({
        "doctype": "Journal Paiement OpenLab", "dossier": dossier, "acteur": acteur, "action": action,
        "motif": motif, "horodatage": now_datetime(),
        "avant": json.dumps(avant, ensure_ascii=False, default=str),
        "apres": json.dumps(apres, ensure_ascii=False, default=str),
    }).insert(ignore_permissions=True)
