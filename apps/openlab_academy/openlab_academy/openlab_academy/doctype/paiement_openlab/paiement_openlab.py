from frappe.model.document import Document


class PaiementOpenLab(Document):
    def validate(self):
        """Une référence n'existe qu'une fois par moyen : une notification rejouée n'enregistre rien de plus."""
        self.cle = f"{self.moyen}|{self.reference}"
