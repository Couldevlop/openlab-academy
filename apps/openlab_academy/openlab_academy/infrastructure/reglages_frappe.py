"""Réglages Frappe de la plateforme (langue, fuseau, devise, marque) tirés de l'écran de réglages."""
import frappe

from openlab_academy.infrastructure import reglages_source_frappe


def _devise(code: str) -> None:
    if not frappe.db.exists("Currency", code):
        frappe.get_doc({"doctype": "Currency", "currency_name": code, "symbol": "FCFA" if code == "XOF" else code,
                        "fraction_units": 0, "enabled": 1}).insert(ignore_permissions=True)
    frappe.db.set_value("Currency", code, "enabled", 1)
    if code == "XOF":
        frappe.db.set_value("Currency", code, {"symbol": "FCFA", "fraction_units": 0})


def _maj(doctype: str, valeurs: dict) -> None:
    doc = frappe.get_single(doctype)
    doc.update(valeurs)
    doc.save(ignore_permissions=True)


def appliquer() -> None:
    marque = reglages_source_frappe.plateforme()
    fuseau = reglages_source_frappe.charger().fuseau
    _devise(marque["devise"])
    _maj("System Settings", {"language": marque["langue"], "time_zone": fuseau, "currency": marque["devise"],
                             "date_format": "dd-mm-yyyy"})
    _maj("Website Settings", {"app_name": marque["nom_plateforme"], "app_logo": marque["logo"],
                              "favicon": marque["logo"]})
    _maj("LMS Settings", {"default_currency": marque["devise"]})
