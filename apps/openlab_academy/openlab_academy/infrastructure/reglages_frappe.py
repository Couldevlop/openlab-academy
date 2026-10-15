"""Réglages de la plateforme : français, Africa/Abidjan, franc CFA, marque OpenLab Academy."""
import frappe

LOGO = "/assets/openlab_academy/images/logo.svg"


def _devise_xof() -> None:
    if not frappe.db.exists("Currency", "XOF"):
        frappe.get_doc({"doctype": "Currency", "currency_name": "XOF", "symbol": "FCFA",
                        "fraction_units": 0, "enabled": 1}).insert(ignore_permissions=True)
    frappe.db.set_value("Currency", "XOF", {"enabled": 1, "symbol": "FCFA", "fraction_units": 0})


def _maj(doctype: str, valeurs: dict) -> None:
    doc = frappe.get_single(doctype)
    doc.update(valeurs)
    doc.save(ignore_permissions=True)


def appliquer() -> None:
    _devise_xof()
    _maj("System Settings", {"language": "fr", "time_zone": "Africa/Abidjan", "currency": "XOF",
                             "date_format": "dd-mm-yyyy"})
    _maj("Website Settings", {"app_name": "OpenLab Academy", "app_logo": LOGO, "favicon": LOGO})
    _maj("LMS Settings", {"default_currency": "XOF"})
