import frappe
from frappe.model.document import Document

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import surcharges_invalidees
from openlab_academy.infrastructure import reglages_evaluation_frappe as console


class SurchargeEvaluationOpenLab(Document):
    def validate(self):
        """Chaque cible atteinte par la surcharge, seule ou combinée aux autres surcharges, garde une chaîne
        valide (y compris au regard de l'option de publication provisoire)."""
        try:
            s = console.surcharge_vers_domaine(self)
        except ReglagesInvalides as e:
            frappe.throw(str(e), title="Surcharge incohérente")
        autres = tuple(console.surcharge_vers_domaine(frappe.get_doc(console.SURCHARGE, nom))
                       for nom in frappe.get_all(console.SURCHARGE, {"name": ["!=", self.name or ""]}, pluck="name",
                                                 order_by="creation"))
        fautives = surcharges_invalidees(console.charger(), (*autres, s), console.exercice_type_yaml, impliquant=s)
        if fautives:
            frappe.throw(console.liste_fautives(fautives), title="Surcharge incohérente")
        filtres = [[champ, "=", valeur] if valeur else [champ, "is", "not set"]
                   for champ, valeur in (("cohorte", self.cohorte), ("exercice", self.exercice))]
        doublon = frappe.db.exists("Surcharge Evaluation OpenLab", [*filtres, ["name", "!=", self.name or ""]])
        if doublon:
            frappe.throw(f"Une surcharge existe déjà pour cette cible ({doublon}) : la priorité serait indéfinie.")
