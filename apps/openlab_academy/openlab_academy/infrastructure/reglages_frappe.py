"""Réglages Frappe de la plateforme (langue, fuseau, devise, marque) tirés de l'écran de réglages."""
import os

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


def _fichier_public(url: str) -> str:
    """URL d'une fiche File pour le logo : le LMS ne résout `banner_image` que par une fiche File, et Frappe n'en
    accepte pas sur /assets ; un logo livré par l'app y est donc recopié dans les fichiers publics (une seule fois)."""
    if not url.startswith("/assets/"):
        return url
    nom = "marque-" + os.path.basename(url)
    existant = frappe.db.get_value("File", {"file_name": nom, "is_private": 0}, "file_url")
    if existant:
        return existant
    # lu dans le dossier public de l'app : sites/assets n'existe pas encore pendant install-app
    app, chemin = url.removeprefix("/assets/").split("/", 1)
    with open(frappe.get_app_path(app, "public", *chemin.split("/")), "rb") as f:
        contenu = f.read()
    return frappe.get_doc({"doctype": "File", "file_name": nom, "is_private": 0,
                           "content": contenu}).insert(ignore_permissions=True).file_url


def appliquer() -> None:
    marque = reglages_source_frappe.plateforme()
    fuseau = reglages_source_frappe.charger().fuseau
    _devise(marque["devise"])
    _maj("System Settings", {"language": marque["langue"], "time_zone": fuseau, "currency": marque["devise"],
                             "date_format": "dd-mm-yyyy"})
    _maj("Website Settings", {"app_name": marque["nom_plateforme"], "app_logo": marque["logo"],
                              "favicon": marque["logo"], "banner_image": _fichier_public(marque["logo"])})
    _maj("LMS Settings", {"default_currency": marque["devise"]})
    # langue, fuseau et devise étant réglés ici, l'assistant d'installation Frappe ne doit plus bloquer le bureau
    for app in frappe.get_all("Installed Application", pluck="name"):
        frappe.db.set_value("Installed Application", app, "is_setup_complete", 1)
    frappe.db.set_single_value("System Settings", "setup_complete", 1)
