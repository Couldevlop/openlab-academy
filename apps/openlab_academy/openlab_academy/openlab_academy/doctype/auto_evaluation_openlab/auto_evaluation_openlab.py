import frappe
from frappe.model.document import Document


class AutoEvaluationOpenLab(Document):
    def validate(self):
        if frappe.db.exists("Auto Evaluation OpenLab",
                            {"apprenant": self.apprenant, "exercice": self.exercice, "name": ["!=", self.name]}):
            frappe.throw("Une auto-évaluation existe déjà pour cet apprenant et cet exercice.")
