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
        filtres = [[champ, "=", valeur] if valeur else [champ, "is", "not set"]
                   for champ, valeur in (("cohorte", self.cohorte), ("exercice", self.exercice))]
        doublon = frappe.db.exists("Surcharge Evaluation OpenLab", [*filtres, ["name", "!=", self.name or ""]])
        if doublon:
            frappe.throw(f"Une surcharge existe déjà pour cette cible ({doublon}) : la priorité serait indéfinie.")
