"""Sites existants : chaque inscription à une cohorte sans dossier de paiement reçoit un dossier dispensé (prix 0)."""
import frappe


def execute():
    for inscription in frappe.get_all("LMS Batch Enrollment", fields=["member", "batch"]):
        cours = frappe.db.get_value("Batch Course", {"parent": inscription.batch}, "course")
        if not cours or frappe.db.exists("Dossier Paiement OpenLab", {"apprenant": inscription.member, "cours": cours}):
            continue
        frappe.get_doc({
            "doctype": "Dossier Paiement OpenLab", "apprenant": inscription.member, "cours": cours,
            "cohorte": inscription.batch, "dispense": 1, "frais_inscription": 0, "prix_une_fois": 0,
            "prix_deux_tranches": 0, "prix_mensuel": 0,
        }).insert(ignore_permissions=True)
