"""Adaptateurs Frappe du paiement : dossiers et paiements, tarifs, réglages."""
import frappe
from frappe.utils import getdate, now_datetime

from openlab_academy.application.ports_paiement import (
    Client, DossierEnregistre, NouveauDossier, PaiementEnregistre, ReglagesPaiement)
from openlab_academy.domain.dossier_paiement import Dossier
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif

DOSSIER = "Dossier Paiement OpenLab"
PAIEMENT = "Paiement OpenLab"


def _lignes(echeances) -> list[dict]:
    return [{"date_limite": e.date_limite, "montant": e.montant, "libelle": e.libelle} for e in echeances]


class DepotDossiersFrappe:
    def charger(self, apprenant: str, cours: str) -> DossierEnregistre | None:
        nom = frappe.db.get_value(DOSSIER, {"apprenant": apprenant, "cours": cours})
        if not nom:
            return None
        d = frappe.get_doc(DOSSIER, nom)
        lot = frappe.db.get_value("LMS Batch", d.cohorte, ["start_date", "end_date"], as_dict=True)
        tarif = Tarif(d.frais_inscription, d.prix_une_fois, d.prix_deux_tranches, d.prix_mensuel)
        echeances = tuple(Echeance(getdate(e.date_limite), e.montant, e.libelle or "") for e in d.echeances)
        dossier = Dossier(echeances, self.paye(nom), getdate(d.delai_jusqu_au) if d.delai_jusqu_au else None,
                          bool(d.dispense), frais_inscription=d.frais_inscription)
        return DossierEnregistre(nom, d.apprenant, d.cours, Mode(d.mode or Mode.UNE_FOIS), d.telephone or "", tarif,
                                 getdate(lot.start_date), getdate(lot.end_date), dossier,
                                 getdate(d.date_inscription or d.creation))

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
        return ReglagesPaiement(valeur("jour_echeance", 10), valeur("inscription_tardive_mois", 2))
