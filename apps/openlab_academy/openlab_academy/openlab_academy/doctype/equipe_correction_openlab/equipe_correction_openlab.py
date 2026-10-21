import frappe
from frappe.model.document import Document

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.infrastructure import reglages_evaluation_frappe as console


class EquipeCorrectionOpenLab(Document):
    def validate(self):
        """Règle du domaine (une cible, au moins un membre ou un responsable, pas de doublon) ; une équipe par
        cible."""
        try:
            console.equipe_vers_domaine(self)
        except ReglagesInvalides as e:
            frappe.throw(str(e), title="Équipe incohérente")
        filtres = [[champ, "=", valeur] if valeur else [champ, "is", "not set"]
                   for champ, valeur in (("cours", self.cours), ("cohorte", self.cohorte), ("exercice", self.exercice))]
        doublon = frappe.db.exists(console.EQUIPE, [*filtres, ["name", "!=", self.name or ""]])
        if doublon:
            frappe.throw(f"Une équipe existe déjà pour cette cible ({doublon}) : la priorité serait indéfinie.")
