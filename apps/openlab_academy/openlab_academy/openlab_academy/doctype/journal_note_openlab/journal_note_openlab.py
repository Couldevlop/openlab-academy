import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

MESSAGE = "Le journal des notes est non modifiable."


class JournalNoteOpenLab(Document):
    def before_insert(self):
        self.horodatage = now_datetime()

    def on_update(self):
        if not self.flags.in_insert:
            frappe.throw(MESSAGE)

    def on_trash(self):
        frappe.throw(MESSAGE)
