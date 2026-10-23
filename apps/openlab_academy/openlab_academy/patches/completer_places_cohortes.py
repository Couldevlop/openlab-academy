"""Sites existants : réglage « places par cohorte » renseigné, et places données aux cohortes ouvertes à
l'inscription autonome qui n'en avaient pas (le LMS y masquait « Enroll Now »)."""
import frappe

from openlab_academy.domain.reglages import Reglages

DOCTYPE = "Reglages OpenLab Academy"


def execute():
    places = frappe.db.get_single_value(DOCTYPE, "places_par_cohorte")
    if not places:
        places = Reglages().places_par_cohorte
        frappe.db.set_single_value(DOCTYPE, "places_par_cohorte", places)
    for lot in frappe.get_all("LMS Batch", {"allow_self_enrollment": 1, "seat_count": ["in", [0, None]]},
                              pluck="name"):
        frappe.db.set_value("LMS Batch", lot, "seat_count", places, update_modified=False)
