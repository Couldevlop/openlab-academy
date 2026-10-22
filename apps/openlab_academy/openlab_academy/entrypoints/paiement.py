"""Points d'accroche de l'inscription : refus des inscriptions tardives ou sans tarif, ouverture du dossier."""
import datetime

import frappe
from frappe.utils import getdate

from openlab_academy.application.paiements import InscriptionTardive, OuvrirDossier, TarifAbsent
from openlab_academy.infrastructure.depot_dossiers_frappe import (
    DepotDossiersFrappe, ReglagesPaiementFrappe, TarifsFrappe)

ROLES_NON_BLOQUES = {"System Manager", "Moderator", "Course Creator", "Batch Evaluator", "Intendant OpenLab"}


def aujourd_hui() -> datetime.date:
    return datetime.date.today()


def _ouvrir() -> OuvrirDossier:
    return OuvrirDossier(DepotDossiersFrappe(), TarifsFrappe(), ReglagesPaiementFrappe(), aujourd_hui)


def _cohorte(doc):
    """(cours, début, fin) de la cohorte ; None pour un rôle exempté ou une cohorte sans parcours."""
    if ROLES_NON_BLOQUES & set(frappe.get_roles(doc.member)):
        return None
    cours = frappe.db.get_value("Batch Course", {"parent": doc.batch}, "course", order_by="idx")
    if not cours:
        return None
    lot = frappe.db.get_value("LMS Batch", doc.batch, ["start_date", "end_date"], as_dict=True)
    return cours, getdate(lot.start_date), getdate(lot.end_date)


def avant_inscription(doc, method=None) -> None:
    lot = _cohorte(doc)
    if lot is None:
        return
    try:
        _ouvrir().verifier(lot[0], lot[1])
    except (InscriptionTardive, TarifAbsent) as e:
        frappe.throw(str(e), exc=frappe.ValidationError)


def apres_inscription(doc, method=None) -> None:
    lot = _cohorte(doc)
    if lot is not None:
        _ouvrir().executer(doc.member, lot[0], doc.batch, lot[1], lot[2])
