"""Adaptateur : journal des ouvertures de leçons (DocType « Ouverture Lecon OpenLab »)."""
import datetime

import frappe
from frappe.utils import get_datetime

DOCTYPE = "Ouverture Lecon OpenLab"
# Int sur LMS Course (créé par entrypoints/install) : délai propre au parcours, 0 = réglage de la plateforme
CHAMP_DELAI = "delai_exercices_minutes"


class DepotOuverturesFrappe:
    def premiere_ouverture(self, apprenant: str, lecon: str) -> datetime.datetime | None:
        valeur = frappe.db.get_value(DOCTYPE, {"apprenant": apprenant, "lecon": lecon}, "ouvert_le",
                                     order_by="ouvert_le asc")
        return get_datetime(valeur) if valeur else None

    def enregistrer(self, apprenant: str, lecon: str, quand: datetime.datetime) -> None:
        frappe.get_doc({"doctype": DOCTYPE, "apprenant": apprenant, "lecon": lecon,
                        "ouvert_le": quand}).insert(ignore_permissions=True)


class DelaiExercicesFrappe:
    """Port DelaiDuParcours : délai réglé sur le parcours de la leçon.

    Rien à dire (champ absent, parcours introuvable, valeur nulle) : l'appelant applique le réglage de la
    plateforme, qui reste la valeur de référence.
    """

    def minutes(self, lecon: str) -> int | None:
        if not frappe.db.has_column("LMS Course", CHAMP_DELAI):
            return None
        cours = frappe.db.get_value("Course Lesson", lecon, "course")
        if not cours:
            return None
        return int(frappe.db.get_value("LMS Course", cours, CHAMP_DELAI) or 0) or None
