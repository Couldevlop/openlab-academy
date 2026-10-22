"""Adaptateurs Frappe du paiement : dossiers et paiements, tarifs, réglages."""
import datetime

import frappe
from frappe.utils import getdate, now_datetime

from openlab_academy.application.ports_paiement import (
    Client, DossierEnregistre, NouveauDossier, PaiementEnregistre, ReferenceDejaEnregistree, ReglagesPaiement)
from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif

DOSSIER = "Dossier Paiement OpenLab"
PAIEMENT = "Paiement OpenLab"
POINT = "enregistrer_virement"
REVERIFICATION_MAX = 500  # paiements revérifiés au plus par passage de la tâche quotidienne


def _lignes(echeances) -> list[dict]:
    return [{"date_limite": e.date_limite, "montant": e.montant, "libelle": e.libelle} for e in echeances]


class DepotDossiersFrappe:
    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None:
        return self.par_nom(frappe.db.get_value(DOSSIER, {"apprenant": apprenant, "cours": cours}))

    def cours_de(self, apprenant: str) -> tuple[str, ...]:
        return tuple(frappe.get_all(DOSSIER, {"apprenant": apprenant}, pluck="cours"))

    def par_nom(self, nom: str | None) -> DossierEnregistre | None:
        if not nom or not frappe.db.exists(DOSSIER, nom):
            return None
        d = frappe.get_doc(DOSSIER, nom)
        lot = frappe.db.get_value("LMS Batch", d.cohorte, ["start_date", "end_date"], as_dict=True)
        inscription = getdate(d.date_inscription or d.creation)  # repli si la cohorte a été supprimée
        tarif = Tarif(d.frais_inscription, d.prix_une_fois, d.prix_deux_tranches, d.prix_mensuel)
        echeances = tuple(Echeance(getdate(e.date_limite), e.montant, e.libelle or "") for e in d.echeances)
        dossier = Dossier(echeances, self.paye(nom), getdate(d.delai_jusqu_au) if d.delai_jusqu_au else None,
                          bool(d.dispense), frais_inscription=d.frais_inscription)
        return DossierEnregistre(nom, d.apprenant, d.cours, Mode(d.mode or Mode.UNE_FOIS), d.telephone or "", tarif,
                                 getdate(lot.start_date) if lot else inscription,
                                 getdate(lot.end_date) if lot else inscription, dossier, inscription)

    def creer(self, d: NouveauDossier) -> str:
        return frappe.get_doc({
            "doctype": DOSSIER, "apprenant": d.apprenant, "cours": d.cours, "cohorte": d.cohorte,
            "mode": d.mode.value, "date_inscription": d.inscription, "frais_inscription": d.tarif.frais_inscription,
            "prix_une_fois": d.tarif.une_fois, "prix_deux_tranches": d.tarif.deux_tranches,
            "prix_mensuel": d.tarif.mensuel, "echeances": _lignes(d.echeances),
        }).insert(ignore_permissions=True).name

    def remplacer_echeances(self, nom: str, mode: Mode, echeances: tuple[Echeance, ...]) -> None:
        d = frappe.get_doc(DOSSIER, nom)
        d.mode = mode.value
        d.set("echeances", _lignes(echeances))
        d.save(ignore_permissions=True)

    def fixer_telephone(self, nom: str, telephone: str) -> None:
        frappe.db.set_value(DOSSIER, nom, "telephone", telephone)

    def paye(self, nom: str) -> int:
        return sum(frappe.get_all(PAIEMENT, {"dossier": nom, "statut": "confirme"}, pluck="montant"))

    def fixer_delai(self, nom: str, d) -> None:
        frappe.db.set_value(DOSSIER, nom, "delai_jusqu_au", d)

    def client(self, apprenant: str) -> Client:
        u = frappe.db.get_value("User", apprenant, ["first_name", "last_name", "email"], as_dict=True) or {}
        return Client(nom=u.get("last_name") or "", prenom=u.get("first_name") or "", email=u.get("email") or "")

    def creer_paiement(self, dossier: str, montant: int, moyen: str, reference: str, statut: str) -> str:
        return frappe.get_doc({"doctype": PAIEMENT, "dossier": dossier, "montant": montant, "moyen": moyen,
                               "reference": reference, "statut": statut}).insert(ignore_permissions=True).name

    def enregistrer_virement(self, dossier: str, montant: int, reference: str, date_paiement, auteur: str) -> None:
        if frappe.db.exists(PAIEMENT, {"cle": f"virement|{reference}"}):
            raise ReferenceDejaEnregistree(reference)
        messages = len(frappe.local.message_log)
        frappe.db.savepoint(POINT)
        try:
            frappe.get_doc({"doctype": PAIEMENT, "dossier": dossier, "montant": montant, "moyen": "virement",
                            "reference": reference, "statut": "confirme", "auteur": auteur,
                            "date_paiement": datetime.datetime.combine(date_paiement, datetime.time())}
                           ).insert(ignore_permissions=True)
        except frappe.UniqueValidationError:  # même référence saisie en même temps par un autre agent
            frappe.db.rollback(save_point=POINT)
            del frappe.local.message_log[messages:]
            raise ReferenceDejaEnregistree(reference) from None

    def _verrouiller(self, moyen: str, reference: str):
        """Ligne du paiement verrouillée jusqu'à la fin de la transaction : deux notifications simultanées
        de la même transaction se suivent au lieu de se croiser."""
        return frappe.db.get_value(PAIEMENT, {"cle": f"{moyen}|{reference}"}, ["name", "statut"], as_dict=True,
                                   for_update=True)

    def paiement(self, moyen: str, reference: str) -> PaiementEnregistre | None:
        p = frappe.db.get_value(PAIEMENT, {"cle": f"{moyen}|{reference}"}, ["name", "dossier", "montant", "statut"],
                                as_dict=True)
        return PaiementEnregistre(p.name, p.dossier, p.montant, p.statut) if p else None

    def confirmer_paiement(self, moyen: str, reference: str, montant: int) -> bool:
        p = self._verrouiller(moyen, reference)
        if not p or p.statut == "confirme":
            return False
        frappe.db.set_value(PAIEMENT, p.name, {"statut": "confirme", "montant": montant,
                                               "date_paiement": now_datetime()})
        return True

    def paiements_en_attente(self, dossier: str, moyen: str, limite: int) -> tuple[str, ...]:
        return tuple(frappe.get_all(PAIEMENT, {"dossier": dossier, "moyen": moyen, "statut": "en_attente"},
                                    pluck="reference", order_by="creation desc", limit=limite))

    def paiements_en_attente_depuis(self, moyen: str, depuis) -> tuple[str, ...]:
        return tuple(frappe.get_all(PAIEMENT, {"moyen": moyen, "statut": "en_attente", "creation": (">=", depuis)},
                                    pluck="reference", order_by="creation desc", limit=REVERIFICATION_MAX))

    def marquer_echoue(self, moyen: str, reference: str) -> None:
        p = self._verrouiller(moyen, reference)
        if p and p.statut == "en_attente":
            frappe.db.set_value(PAIEMENT, p.name, "statut", "echoue")


class TarifsFrappe:
    def charger(self, cours: str) -> Tarif | None:
        t = frappe.db.get_value("Tarif Parcours OpenLab", cours,
                                ["frais_inscription", "prix_une_fois", "prix_deux_tranches", "prix_mensuel"])
        return Tarif(*t) if t else None


class ReglagesPaiementFrappe:
    def charger(self) -> ReglagesPaiement:
        def valeur(champ, defaut):
            return int(frappe.db.get_single_value("Reglages Paiement OpenLab", champ) or defaut)
        delais = frappe.db.get_single_value("Reglages Paiement OpenLab", "delais_rappel") or "7,3,1"
        return ReglagesPaiement(valeur("jour_echeance", 10), valeur("inscription_tardive_mois", 2),
                                tuple(int(m) for m in delais.split(",")))  # validés à l'enregistrement
