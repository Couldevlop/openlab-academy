import frappe
from frappe.model.document import Document

from openlab_academy.domain.echeancier import Tarif, TarifInvalide


class TarifParcoursOpenLab(Document):
    def validate(self):
        """Les montants respectent le domaine : positifs, multiples de 5, prix croissants."""
        try:
            Tarif(int(self.frais_inscription or 0), int(self.prix_une_fois or 0), int(self.prix_deux_tranches or 0),
                  int(self.prix_mensuel or 0)).valider()
        except TarifInvalide as e:
            frappe.throw(str(e), title="Tarif invalide")
