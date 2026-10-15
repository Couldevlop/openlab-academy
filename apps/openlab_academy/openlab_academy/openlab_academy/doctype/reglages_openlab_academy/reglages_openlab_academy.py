import frappe
from frappe.model.document import Document

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.infrastructure.reglages_source_frappe import vers_domaine


class ReglagesOpenLabAcademy(Document):
    def validate(self):
        """Les invariants du domaine s'appliquent à toute modification faite dans l'écran."""
        try:
            vers_domaine(self)
        except ReglagesInvalides as e:
            frappe.throw(str(e), title="Réglages incohérents")
