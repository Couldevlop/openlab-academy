"""Une famille de parcours, administrable.

Le formulaire refuse une teinte sur laquelle un titre blanc ne se lit pas. C'est la seule limite
posée au choix de l'administration, et elle tient à l'accessibilité : la bande de couleur porte le
titre du parcours, une couleur trop claire le rend illisible pour une partie des visiteurs.
"""
import frappe
from frappe import _
from frappe.model.document import Document

from openlab_academy.domain.domaine import TeinteIllisible, verifier_teinte


class DomaineOpenLab(Document):
    def validate(self) -> None:
        self.cle = (self.cle or "").strip()
        try:
            self.teinte = verifier_teinte(self.teinte)
        except TeinteIllisible as e:
            frappe.throw(str(e), frappe.ValidationError)
        if not self.cle.replace("-", "").replace("_", "").isalnum() or not self.cle.isascii():
            frappe.throw(
                _("La cle doit s'ecrire sans accent ni espace : lettres, chiffres, tiret ou tiret bas."),
                frappe.ValidationError)
        if self.cle != self.cle.lower():
            # « IA » et « ia » donneraient deux familles pour une seule : la reconnaissance d'un
            # coup d'oeil, seule raison d'etre de la couleur, s'effondrerait.
            frappe.throw(_("La cle s'ecrit en minuscules."), frappe.ValidationError)
