"""Point d'accroche : une soumission de devoir LMS devient une copie OpenLab figée.

Ne bloque jamais le dépôt de l'apprenant : toute erreur interne est consignée et le dépôt LMS se poursuit.
"""
import frappe
from frappe.utils import now_datetime

from openlab_academy.application.soumettre_copie import SoumettreCopie
from openlab_academy.infrastructure import reglages_evaluation_frappe
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe
from openlab_academy.infrastructure.instantane_provisoire import InstantaneProvisoire

CHAMPS = ("name", "assignment", "member", "type", "answer", "assignment_attachment")


def soumettre(soumission: dict) -> str | None:
    return SoumettreCopie(DepotCopiesFrappe(), InstantaneProvisoire(), reglages_evaluation_frappe.charger(),
                          now_datetime, reglages_evaluation_frappe.surcharges).executer(soumission)


def rendu(doc, method=None) -> None:
    try:
        soumettre({champ: doc.get(champ) for champ in CHAMPS})
    except Exception:
        frappe.log_error(title="openlab_academy : copie non créée", message=frappe.get_traceback())
