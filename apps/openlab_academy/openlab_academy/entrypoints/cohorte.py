"""Commande : bench --site <site> execute openlab_academy.entrypoints.cohorte.ouvrir_pilote
             [--kwargs "{'rythme': '<code réglé dans l'écran>'}"]"""
import frappe
from frappe.utils import getdate, nowdate

from openlab_academy.application.ouvrir_cohorte import OuvrirCohorte
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier


def ouvrir_pilote(rythme: str | None = None, commit: bool = True) -> dict:
    reglages = reglages_source_frappe.charger()
    format_ = reglages.rythme(rythme) if rythme else reglages.rythmes[0]
    parcours = next((p for p in charger_dossier(PARCOURS_DIR, reglages) if p.title == reglages.parcours_pilote), None)
    if parcours is None:
        raise ValueError(f"parcours pilote « {reglages.parcours_pilote} » introuvable dans les fichiers de parcours")
    nom, creee = OuvrirCohorte(DepotCohortesFrappe(reglages.formateur), reglages,
                         aujourd_hui=lambda: getdate(nowdate())).executer(parcours, rythme=format_)
    if commit:
        frappe.db.commit()
    return {"cohorte": nom, "creee": creee}
