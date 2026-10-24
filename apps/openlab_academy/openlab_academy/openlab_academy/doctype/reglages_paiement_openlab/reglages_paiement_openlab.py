import frappe
from frappe.model.document import Document

from openlab_academy.infrastructure.canaux import url_jeton_valide


class ReglagesPaiementOpenLab(Document):
    def validate(self):
        if not 1 <= int(self.jour_echeance or 0) <= 28:
            frappe.throw("Le jour d'échéance doit être compris entre 1 et 28.", title="Réglages de paiement")
        if int(self.inscription_tardive_mois or 0) < 0:
            frappe.throw("Le délai d'inscription tardive ne peut pas être négatif.", title="Réglages de paiement")
        delais = [m.strip() for m in (self.delais_rappel or "").split(",")]
        if not all(m.isdigit() and int(m) > 0 for m in delais) or len(set(map(int, delais))) != len(delais):
            frappe.throw("Les délais de rappel sont des entiers positifs distincts séparés par des virgules.",
                         title="Réglages de paiement")
        if not url_jeton_valide(self.sms_url_jeton):
            frappe.throw("L'URL du jeton SMS doit être en https sur orange.com (ou un de ses sous-domaines).",
                         title="Réglages de paiement")
