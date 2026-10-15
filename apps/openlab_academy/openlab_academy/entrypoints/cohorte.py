"""Commande : bench --site <site> execute openlab_academy.entrypoints.cohorte.ouvrir_pilote"""
import frappe

from openlab_academy.application.ouvrir_cohorte import OuvrirCohorte
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

PARCOURS_PILOTE = "Fondamentaux de la Data Science"


def ouvrir_pilote(commit: bool = True) -> dict:
    parcours = next(p for p in charger_dossier(PARCOURS_DIR) if p.title == PARCOURS_PILOTE)
    nom, creee = OuvrirCohorte(DepotCohortesFrappe()).executer(parcours)
    if commit:
        frappe.db.commit()
    return {"cohorte": nom, "creee": creee}
