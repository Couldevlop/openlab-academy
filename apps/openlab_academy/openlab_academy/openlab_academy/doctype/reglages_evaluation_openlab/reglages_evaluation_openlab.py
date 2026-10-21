import frappe
from frappe.model.document import Document

from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import surcharges_invalidees
from openlab_academy.infrastructure import reglages_evaluation_frappe as console


class ReglagesEvaluationOpenLab(Document):
    def validate(self):
        """Les invariants du domaine s'appliquent à toute modification faite dans la console ; un changement qui
        rendrait invalide une surcharge jusque-là valide est refusé, avec la liste des surcharges concernées."""
        try:
            nouveaux = console.vers_domaine(self)
        except ReglagesInvalides as e:
            frappe.throw(str(e), title="Réglages d'évaluation incohérents")
        surcharges = console.surcharges()
        if not surcharges:
            return
        avant = console.charger()
        deja = {libelle for libelle, _ in surcharges_invalidees(avant, surcharges, console.exercice_type_yaml)}
        fautives = [(libelle, motif) for libelle, motif in
                    surcharges_invalidees(nouveaux, surcharges, console.exercice_type_yaml) if libelle not in deja]
        if fautives:
            frappe.throw(f"Ces réglages invalideraient {len(fautives)} surcharge(s) : "
                         f"{console.liste_fautives(fautives)}", title="Réglages d'évaluation incohérents")
