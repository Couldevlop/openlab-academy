import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class DelegationOpenLab(Document):
    def validate(self):
        if self.titulaire == self.delegataire:
            frappe.throw("Le titulaire et le délégataire doivent être deux personnes différentes.")
        if get_datetime(self.fin) <= get_datetime(self.debut):
            frappe.throw("La fin doit suivre le début de la délégation.")
