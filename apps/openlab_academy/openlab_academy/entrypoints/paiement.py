"""Points d'accroche de l'inscription (refus des inscriptions tardives ou sans tarif, ouverture du dossier) et
assemblage du paiement en ligne CinetPay (réglages, liens de retour et de notification)."""
import datetime
from urllib.parse import urlencode, urlsplit

import frappe
from frappe.utils import getdate, now_datetime

from openlab_academy.application.paiements import (
    ConfirmerPaiement, InitierPaiement, InscriptionTardive, OuvrirDossier, PaiementIndisponible, TarifAbsent)
from openlab_academy.entrypoints.lms import ROLES_NON_BLOQUES
from openlab_academy.infrastructure.cinetpay import PasserelleCinetPay
from openlab_academy.infrastructure.depot_dossiers_frappe import (
    DepotDossiersFrappe, ReglagesPaiementFrappe, TarifsFrappe)
from openlab_academy.infrastructure.journal_paiement_frappe import journaliser

REGLAGES = "Reglages Paiement OpenLab"
API = "/api/method/openlab_academy.entrypoints.paiement_api"


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


# --- paiement en ligne -----------------------------------------------------------------------------------
def passerelle() -> PasserelleCinetPay:
    """Passerelle CinetPay des réglages ; les clés sont lues déchiffrées, sans jamais quitter l'adaptateur."""
    r = frappe.get_single(REGLAGES)
    return PasserelleCinetPay(r.cinetpay_site_id or "", r.get_password("cinetpay_api_key", raise_exception=False) or "",
                              r.get_password("cinetpay_secret", raise_exception=False) or "")


def liens(cours: str) -> tuple[str, str]:
    """(URL de retour, URL de notification) sur l'adresse publique réglée ; indisponible si elle est invalide."""
    base = (frappe.db.get_single_value(REGLAGES, "cinetpay_url_notification_base") or "").strip().rstrip("/")
    parties = urlsplit(base)
    if (parties.scheme not in ("http", "https") or not parties.hostname or "@" in parties.netloc
            or parties.query or parties.fragment):
        raise PaiementIndisponible("Le paiement en ligne n'est pas disponible pour le moment.")
    return (f"{base}{API}.retour_cinetpay?{urlencode({'cours': cours})}", f"{base}{API}.notification_cinetpay")


def initier_paiement(apprenant: str, cours: str) -> str:
    """URL de la page de paiement CinetPay de la part due de la prochaine échéance."""
    return InitierPaiement(DepotDossiersFrappe(), passerelle(), now_datetime, liens).executer(apprenant, cours)


def confirmer_paiement(transaction: str, p: PasserelleCinetPay | None = None) -> None:
    ConfirmerPaiement(DepotDossiersFrappe(), p or passerelle(), journaliser).executer(transaction)


def reconcilier_paiements(apprenant: str, cours: str) -> None:
    ConfirmerPaiement(DepotDossiersFrappe(), passerelle(), journaliser).reconcilier(apprenant, cours)
