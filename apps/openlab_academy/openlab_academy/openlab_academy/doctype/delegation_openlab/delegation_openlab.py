import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from openlab_academy.domain.delegation import DelegationRefusee, verifier_delegation
from openlab_academy.infrastructure import delegations_frappe, journal_frappe
from openlab_academy.infrastructure.reglages_evaluation_frappe import delegation_vers_domaine

CHAMPS = ("titulaire", "delegataire", "debut", "fin", "cours", "cohorte", "exercice")


def _notifier(destinataire: str, message: str) -> None:
    from openlab_academy.entrypoints import evaluation  # point d'entrée : alerte et courriel des notifications
    evaluation.notifier(destinataire, message)


class DelegationOpenLab(Document):
    """Écran de la console et API passent par ici : même règle (domaine), même journal, mêmes notifications."""

    def validate(self):
        avant = self.get_doc_before_save()
        if avant and not avant.revoquee and self.revoquee and all(self.get(c) == avant.get(c) for c in CHAMPS):
            return  # une révocation est toujours possible, même si les habilitations ont changé depuis
        d = delegation_vers_domaine(self)
        try:
            verifier_delegation(d, delegations_frappe.faits(d), now_datetime(), self.is_new())
        except DelegationRefusee as e:
            frappe.throw(str(e), title="Délégation refusée")

    def _valeurs(self) -> dict:
        return {c: self.get(c) for c in CHAMPS}

    def _consigner(self, action: str, avant: dict, apres: dict) -> None:
        journal_frappe.journaliser(f"délégation:{self.name}", frappe.session.user, action, avant, apres)
        perimetre = " / ".join(str(self.get(c)) for c in ("cours", "cohorte", "exercice") if self.get(c)) or "tout"
        for destinataire, role in ((self.titulaire, "titulaire"), (self.delegataire, "délégataire")):
            _notifier(destinataire, f"{action.capitalize()} : vous êtes {role} de la délégation {self.name} "
                                    f"({self.titulaire} → {self.delegataire}, périmètre : {perimetre}, "
                                    f"jusqu'au {self.fin}).")

    def after_insert(self):
        self._consigner("délégation créée", {}, self._valeurs())

    def on_update(self):
        avant = self.get_doc_before_save()
        if avant is None:  # création : déjà consignée par after_insert
            return
        if not avant.revoquee and self.revoquee:
            self._consigner("délégation révoquée", {"revoquee": False}, {"revoquee": True})
        elif any(self.get(c) != avant.get(c) for c in CHAMPS):
            self._consigner("délégation modifiée", {c: avant.get(c) for c in CHAMPS}, self._valeurs())
