from frappe.model.document import Document


class RappelPaiementOpenLab(Document):
    def validate(self):
        """Un rappel ne part qu'une fois par dossier, échéance, délai et canal."""
        self.cle = f"{self.dossier}|{self.date_limite}|{self.jours_avant}|{self.canal}"
