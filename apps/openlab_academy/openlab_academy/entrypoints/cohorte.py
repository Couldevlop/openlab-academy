"""Commande : bench --site <site> execute openlab_academy.entrypoints.cohorte.ouvrir_pilote"""
import frappe

from openlab_academy.application.ouvrir_cohorte import OuvrirCohorte
from openlab_academy.domain.cohorte import Rythme
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier

PARCOURS_PILOTE = "Fondamentaux de la Data Science"


def ouvrir_pilote(rythme: str = "standard", commit: bool = True) -> dict:
    """bench execute ... --kwargs "{'rythme': 'intensif'}" pour une cohorte intensive."""
    try:
        format_ = Rythme(rythme)
    except ValueError:
        raise ValueError(f"rythme « {rythme} » inconnu : {[r.value for r in Rythme]}") from None
    parcours = next(p for p in charger_dossier(PARCOURS_DIR) if p.title == PARCOURS_PILOTE)
    nom, creee = OuvrirCohorte(DepotCohortesFrappe()).executer(parcours, rythme=format_)
    if commit:
        frappe.db.commit()
    return {"cohorte": nom, "creee": creee}
