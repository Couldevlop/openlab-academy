"""Point d'accroche : une soumission de devoir LMS devient une copie OpenLab figée.

Ne bloque jamais le dépôt de l'apprenant : toute erreur interne est consignée, les écritures partielles sont
annulées (point de sauvegarde) et le dépôt LMS se poursuit.
"""
import frappe
from frappe.utils import now_datetime

from openlab_academy.application.soumettre_copie import SoumettreCopie
from openlab_academy.infrastructure import journal_frappe, reglages_evaluation_frappe
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe, cours_evalue
from openlab_academy.infrastructure.instantane_provisoire import InstantaneProvisoire

CHAMPS = ("name", "assignment", "member", "type", "answer", "assignment_attachment")
POINT = "openlab_rendu"


def soumettre(soumission: dict) -> str | None:
    return SoumettreCopie(DepotCopiesFrappe(), InstantaneProvisoire(), reglages_evaluation_frappe.charger(),
                          now_datetime, reglages_evaluation_frappe.surcharges,
                          journal_frappe.journaliser).executer(soumission)


def rendu(doc, method=None) -> None:
    soumission = {champ: doc.get(champ) for champ in CHAMPS}
    frappe.db.savepoint(POINT)
    try:
        copie = soumettre(soumission)
        if copie is None and method != "on_update" and cours_evalue(soumission["assignment"]):
            frappe.log_error(title="openlab_academy : exercice sans grille",
                             message=f"Le devoir {soumission['assignment']} n'a pas de grille OpenLab : "
                                     f"la soumission {soumission['name']} n'a pas de copie.")
    except Exception:
        frappe.db.rollback(save_point=POINT)
        frappe.log_error(title="openlab_academy : copie non créée", message=frappe.get_traceback())
