"""Commande : bench --site <site> execute openlab_academy.entrypoints.seed.run

Racine de composition : réglages (écran) -> source YAML -> cas d'usage -> dépôt Frappe.
"""
import pathlib

import frappe

from openlab_academy.application.publier_parcours import PublierParcours
from openlab_academy.infrastructure import reglages_evaluation_frappe, reglages_source_frappe
from openlab_academy.infrastructure.depot_frappe import DepotFrappe
from openlab_academy.infrastructure.yaml_source import PARCOURS_DIR, charger_dossier


def _journal(message: str) -> None:
    frappe.log_error(title="openlab_academy : publication des parcours", message=message)


def run(path: str | None = None, commit: bool = True) -> dict[str, str]:
    reglages = reglages_source_frappe.charger()
    lot = charger_dossier(pathlib.Path(path) if path else PARCOURS_DIR, reglages)
    statuts = PublierParcours(DepotFrappe(commit=commit, reglages=reglages, evaluation=reglages_evaluation_frappe.charger()), _journal).executer(lot)
    resultat = {titre: statut.value for titre, statut in statuts.items()}
    print(resultat)
    return resultat
