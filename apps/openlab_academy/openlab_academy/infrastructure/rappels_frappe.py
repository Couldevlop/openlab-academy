"""Adaptateurs Frappe des rappels de paiement : dossiers à rappeler et registre `Rappel Paiement OpenLab`."""
from urllib.parse import quote

import frappe
from frappe.utils import get_url, getdate

from openlab_academy.application.rappels import ECHEC, ENVOYE, Destinataire, DossierARappeler
from openlab_academy.infrastructure.depot_dossiers_frappe import DOSSIER, DepotDossiersFrappe

RAPPEL = "Rappel Paiement OpenLab"
POINT = "openlab_rappel_reserve"


class DepotRappelsFrappe:
    def noms(self) -> tuple[str, ...]:
        return tuple(frappe.get_all(DOSSIER, {"dispense": 0}, pluck="name", order_by="creation"))

    def charger(self, nom: str) -> DossierARappeler | None:
        d = DepotDossiersFrappe().par_nom(nom)
        if d is None:
            return None
        u = frappe.db.get_value("User", d.apprenant, ["email", "full_name"], as_dict=True) or {}
        titre = frappe.db.get_value("LMS Course", d.cours, "title") or d.cours
        return DossierARappeler(d.nom, d.cours, titre,
                                Destinataire(u.get("email") or "", d.telephone, u.get("full_name") or ""), d.dossier,
                                get_url(f"/espace/paiement/{quote(d.cours, safe='')}"))


def _cle(dossier, date_limite, jours, canal) -> str:
    return f"{dossier}|{date_limite}|{jours}|{canal}"  # même clé que le DocType


class RegistreRappelsFrappe:
    def etats(self, dossier: str) -> dict:
        return {(getdate(r.date_limite), r.jours_avant, r.canal): r.statut
                for r in frappe.get_all(RAPPEL, {"dossier": dossier}, ["date_limite", "jours_avant", "canal", "statut"])}

    def reserver(self, dossier: str, date_limite, jours: int, canal: str) -> bool:
        """Ligne verrouillée jusqu'à la validation du dossier : une seconde tâche simultanée attend puis la voit
        `envoye`. Absente, elle est créée `echec` (relançable si l'envoi n'aboutit pas)."""
        cle = _cle(dossier, date_limite, jours, canal)
        ligne = frappe.db.get_value(RAPPEL, {"cle": cle}, ["name", "statut"], as_dict=True, for_update=True)
        if ligne:
            if ligne.statut == ENVOYE:
                return False
            if ligne.statut != ECHEC:
                frappe.db.set_value(RAPPEL, ligne.name, "statut", ECHEC)
            return True
        return self._creer(dossier, date_limite, jours, canal, ECHEC)  # False : réservé au même instant ailleurs

    def consigner(self, dossier: str, date_limite, jours: int, canal: str, statut: str) -> None:
        cle = _cle(dossier, date_limite, jours, canal)
        nom = frappe.db.get_value(RAPPEL, {"cle": cle})
        if not nom:
            if self._creer(dossier, date_limite, jours, canal, statut):
                return
            nom = frappe.db.get_value(RAPPEL, {"cle": cle})  # créée au même instant par une autre tâche
        frappe.db.set_value(RAPPEL, nom, "statut", statut)

    def _creer(self, dossier, date_limite, jours, canal, statut) -> bool:
        """Crée la ligne ; False (sans trace ni message) si la clé existe déjà."""
        messages = len(frappe.local.message_log)
        frappe.db.savepoint(POINT)
        try:
            frappe.get_doc({"doctype": RAPPEL, "dossier": dossier, "date_limite": date_limite, "jours_avant": jours,
                            "canal": canal, "statut": statut}).insert(ignore_permissions=True)
        except frappe.UniqueValidationError:
            frappe.db.rollback(save_point=POINT)
            del frappe.local.message_log[messages:]
            return False
        return True
