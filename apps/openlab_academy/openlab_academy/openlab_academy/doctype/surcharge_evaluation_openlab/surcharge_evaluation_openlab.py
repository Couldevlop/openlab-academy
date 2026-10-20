import frappe
from frappe.model.document import Document

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import TypeExercice
from openlab_academy.infrastructure import reglages_evaluation_frappe as console


class SurchargeEvaluationOpenLab(Document):
    def validate(self):
        """La surcharge doit être une chaîne valide, y compris au regard de l'option de publication provisoire."""
        try:
            s = console.surcharge_vers_domaine(self)
            console.charger().chaine_pour(TypeExercice.LIVRABLE, s.cohorte, s.exercice, (s,), None)
        except ReglagesInvalides as e:
            frappe.throw(str(e), title="Surcharge incohérente")
