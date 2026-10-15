"""Adaptateur de sortie : cohortes du domaine -> doctype LMS Batch."""
import frappe

from openlab_academy.domain.cohorte import Cohorte

class DepotCohortesFrappe:
    def __init__(self, formateur: str = "Administrator"):
        self._formateur = formateur

    def trouver(self, titre: str) -> str | None:
        return frappe.db.get_value("LMS Batch", {"title": titre})

    def creer(self, cohorte: Cohorte) -> str:
        cours = frappe.db.get_value("LMS Course", {"title": cohorte.cours})
        if not cours:
            raise ValueError(f"cours « {cohorte.cours} » introuvable : publiez les parcours d'abord")
        return frappe.get_doc({
            "doctype": "LMS Batch", "title": cohorte.titre, "published": 1, "medium": "Online",
            "start_date": cohorte.debut, "end_date": cohorte.fin,
            "start_time": cohorte.heure_debut, "end_time": cohorte.heure_fin, "timezone": cohorte.fuseau,
            "description": "Cohorte pilote en soirée : modules hebdomadaires, semaines projet, capstone devant jury.",
            "batch_details": (f"<p><b>Format {cohorte.rythme.libelle.lower()}</b> — {cohorte.rythme.descriptif}.</p>"
                              "<p>Séances du soir de 18 h 30 à 20 h 30 (heure d'Abidjan).</p>"),
            "instructors": [{"instructor": self._formateur}], "courses": [{"course": cours}],
            "allow_self_enrollment": 1, "certification": 1, "evaluation": 1,
        }).insert(ignore_permissions=True).name
