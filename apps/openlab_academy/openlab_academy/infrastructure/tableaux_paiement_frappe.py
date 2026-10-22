"""Adaptateur Frappe des tableaux du paiement : lectures groupées (dossiers, échéances, payé, identités, titres),
encaissements par période, paiements, rappels et journal d'un dossier.

Toutes les valeurs de filtre passent en paramètres (filtres Frappe ou constructeur de requêtes), jamais dans le
texte SQL. Aucun statut n'est calculé ici : seul le domaine en décide, à partir des dossiers rendus.
"""
import datetime
import json

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import getdate

from openlab_academy.application.ports_paiement import FiltresTableau, LigneDossier
from openlab_academy.domain.echeancier import Mode
from openlab_academy.infrastructure.depot_dossiers_frappe import DOSSIER, PAIEMENT, vers_dossier

ECHEANCE = "Echeance Paiement OpenLab"
RAPPEL = "Rappel Paiement OpenLab"
JOURNAL = "Journal Paiement OpenLab"
CHAMPS = ["name", "apprenant", "cours", "cohorte", "mode", "date_inscription", "creation", "dispense",
          "delai_jusqu_au", "frais_inscription"]


def _texte(valeur) -> str | None:
    return None if valeur is None else str(valeur)


def _json(valeur):
    try:
        return json.loads(valeur) if valeur else {}
    except ValueError:
        return valeur


def _par_cle(lignes, cle: str, valeur: str) -> dict:
    return {x[cle]: x[valeur] for x in lignes}


class TableauxPaiementFrappe:
    def dossiers(self, f: FiltresTableau) -> tuple[LigneDossier, ...]:
        filtres = [[DOSSIER, champ, "=", v] for champ, v in
                   (("cours", f.parcours), ("cohorte", f.cohorte), ("mode", f.mode.value if f.mode else None)) if v]
        filtres += [[DOSSIER, "date_inscription", op, d] for op, d in ((">=", f.du), ("<=", f.au)) if d]
        return self._construire(frappe.get_all(DOSSIER, filters=filtres, fields=CHAMPS,
                                               order_by="date_inscription desc, name asc"))

    def ligne(self, nom: str) -> LigneDossier | None:
        lignes = self._construire(frappe.get_all(DOSSIER, filters={"name": nom}, fields=CHAMPS))
        return lignes[0] if lignes else None

    def _construire(self, rangees) -> tuple[LigneDossier, ...]:
        if not rangees:
            return ()
        noms = [r.name for r in rangees]
        e = frappe.qb.DocType(ECHEANCE)
        echeances: dict[str, list] = {}
        for x in (frappe.qb.from_(e).select(e.parent, e.date_limite, e.montant, e.libelle)
                  .where((e.parenttype == DOSSIER) & (e.parentfield == "echeances") & e.parent.isin(noms))
                  .orderby(e.parent).orderby(e.idx).run(as_dict=True)):
            echeances.setdefault(x.parent, []).append(x)
        p = frappe.qb.DocType(PAIEMENT)
        payes = _par_cle(frappe.qb.from_(p).select(p.dossier, Sum(p.montant).as_("paye"))
                         .where((p.statut == "confirme") & p.dossier.isin(noms)).groupby(p.dossier)
                         .run(as_dict=True), "dossier", "paye")
        personnes = {u.name: u for u in frappe.get_all(
            "User", filters={"name": ["in", sorted({r.apprenant for r in rangees})]},
            fields=["name", "full_name", "email"])}
        titres = _par_cle(frappe.get_all("LMS Course", filters={"name": ["in", sorted({r.cours for r in rangees})]},
                                         fields=["name", "title"]), "name", "title")
        lignes = []
        for r in rangees:
            u = personnes.get(r.apprenant) or frappe._dict()
            lignes.append(LigneDossier(
                r.name, r.apprenant, u.full_name or r.apprenant, u.email or "", r.cours,
                titres.get(r.cours) or r.cours, r.cohorte or "", Mode(r.mode or Mode.UNE_FOIS),
                getdate(r.date_inscription or r.creation),
                vers_dossier(echeances.get(r.name, ()), int(payes.get(r.name) or 0), r.delai_jusqu_au, r.dispense,
                             r.frais_inscription)))
        return tuple(lignes)

    def encaisse(self, du: datetime.date, au: datetime.date, dossiers: tuple[str, ...] | None = None) -> int:
        if dossiers is not None and not dossiers:
            return 0
        p = frappe.qb.DocType(PAIEMENT)
        condition = ((p.statut == "confirme") & (p.date_paiement >= datetime.datetime.combine(du, datetime.time()))
                     & (p.date_paiement < datetime.datetime.combine(au + datetime.timedelta(days=1),
                                                                    datetime.time())))
        if dossiers is not None:
            condition &= p.dossier.isin(list(dossiers))
        (total,), = frappe.qb.from_(p).select(Sum(p.montant)).where(condition).run()
        return int(total or 0)

    def paiements(self, dossier: str) -> tuple[dict, ...]:
        return tuple({"montant": x.montant, "moyen": x.moyen, "reference": x.reference, "statut": x.statut,
                      "date_paiement": _texte(x.date_paiement), "auteur": x.auteur or "", "cree": _texte(x.creation)}
                     for x in frappe.get_all(PAIEMENT, filters={"dossier": dossier},
                                             fields=["montant", "moyen", "reference", "statut", "date_paiement",
                                                     "auteur", "creation"], order_by="creation desc"))

    def rappels(self, dossier: str) -> tuple[dict, ...]:
        return tuple({"date_limite": _texte(x.date_limite), "jours_avant": x.jours_avant, "canal": x.canal,
                      "statut": x.statut, "cree": _texte(x.creation)}
                     for x in frappe.get_all(RAPPEL, filters={"dossier": dossier},
                                             fields=["date_limite", "jours_avant", "canal", "statut", "creation"],
                                             order_by="creation desc"))

    def journal(self, dossier: str | None, limite: int) -> tuple[dict, ...]:
        return tuple({"dossier": x.dossier, "acteur": x.acteur, "action": x.action, "motif": x.motif or "",
                      "horodatage": _texte(x.horodatage), "avant": _json(x.avant), "apres": _json(x.apres)}
                     for x in frappe.get_all(JOURNAL, filters={"dossier": dossier} if dossier else {},
                                             fields=["dossier", "acteur", "action", "motif", "horodatage", "avant",
                                                     "apres"],
                                             order_by="horodatage desc, creation desc", limit=limite))
