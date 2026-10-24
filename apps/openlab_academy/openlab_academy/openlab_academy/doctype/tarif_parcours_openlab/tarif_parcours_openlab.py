import frappe
from frappe.model.document import Document

from openlab_academy.application.parcours_gratuits import TarifSurParcoursGratuit, refuser_tarif_si_gratuit
from openlab_academy.domain.echeancier import Tarif, TarifInvalide
from openlab_academy.infrastructure.depot_dossiers_frappe import ParcoursGratuitsFrappe


class TarifParcoursOpenLab(Document):
    def validate(self):
        """Aucun tarif sur un parcours gratuit ; les montants respectent le domaine : positifs, multiples de 5, prix
        croissants."""
        try:
            refuser_tarif_si_gratuit(ParcoursGratuitsFrappe(), self.cours)
        except TarifSurParcoursGratuit as e:
            frappe.throw(str(e), title="Parcours gratuit")
        try:
            Tarif(int(self.frais_inscription or 0), int(self.prix_une_fois or 0), int(self.prix_deux_tranches or 0),
                  int(self.prix_mensuel or 0)).valider()
        except TarifInvalide as e:
            frappe.throw(str(e), title="Tarif invalide")
