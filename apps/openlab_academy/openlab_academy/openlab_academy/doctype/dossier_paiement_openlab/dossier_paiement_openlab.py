from frappe.model.document import Document


class DossierPaiementOpenLab(Document):
    def validate(self):
        """Clé portée par un index unique : un seul dossier par apprenant et par parcours, même en concurrence."""
        self.cle = f"{self.apprenant}|{self.cours}"
