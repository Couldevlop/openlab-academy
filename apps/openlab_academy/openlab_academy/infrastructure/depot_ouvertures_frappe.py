"""Adaptateur : journal des ouvertures de leçons (DocType « Ouverture Lecon OpenLab »)."""
import datetime

import frappe
from frappe.utils import get_datetime

DOCTYPE = "Ouverture Lecon OpenLab"


class DepotOuverturesFrappe:
    def premiere_ouverture(self, apprenant: str, lecon: str) -> datetime.datetime | None:
        valeur = frappe.db.get_value(DOCTYPE, {"apprenant": apprenant, "lecon": lecon}, "ouvert_le",
                                     order_by="ouvert_le asc")
        return get_datetime(valeur) if valeur else None

    def enregistrer(self, apprenant: str, lecon: str, quand: datetime.datetime) -> None:
        frappe.get_doc({"doctype": DOCTYPE, "apprenant": apprenant, "lecon": lecon,
                        "ouvert_le": quand}).insert(ignore_permissions=True)
