"""Adaptateur de sortie : les parcours offerts, un couple (apprenant, parcours) à la fois.

Une ligne présente vaut gratuité accordée ; retirée, le parcours redevient payant pour cette personne. Le
document garde qui a offert, quand et pourquoi : c'est la trace que l'intendance relira.
"""
import frappe

DOCTYPE = "Gratuite Apprenant OpenLab"


class GratuitesFrappe:
    def accordee(self, apprenant: str, cours: str) -> bool:
        return bool(frappe.db.exists(DOCTYPE, {"apprenant": apprenant, "parcours": cours}))

    def accorder(self, apprenant: str, cours: str, acteur: str, motif: str = "") -> None:
        if self.accordee(apprenant, cours):
            return
        frappe.get_doc({"doctype": DOCTYPE, "apprenant": apprenant, "parcours": cours,
                        "accordee_le": frappe.utils.now(), "accordee_par": acteur,
                        "motif": motif}).insert(ignore_permissions=True)

    def retirer(self, apprenant: str, cours: str) -> None:
        for nom in frappe.get_all(DOCTYPE, {"apprenant": apprenant, "parcours": cours}, pluck="name"):
            frappe.delete_doc(DOCTYPE, nom, ignore_permissions=True, delete_permanently=True)

    def apprenants(self, cours: str) -> tuple[str, ...]:
        return tuple(frappe.get_all(DOCTYPE, {"parcours": cours}, pluck="apprenant", order_by="apprenant asc"))

    def parcours(self, apprenant: str) -> tuple[str, ...]:
        return tuple(frappe.get_all(DOCTYPE, {"apprenant": apprenant}, pluck="parcours"))
