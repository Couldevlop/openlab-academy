"""Points d'API du paiement : notification et retour CinetPay.

La notification est un appel serveur à serveur sans session (Guest) : Frappe ne lui demande pas de jeton CSRF, la
preuve d'origine est l'en-tête `x-token` (HMAC de la clé secrète), puis le statut et le montant sont toujours relus
auprès de CinetPay avant toute écriture. Elle répond 200 dans tous les cas (sinon CinetPay la rejoue) et consigne
les refus sans aucun secret. Le retour ne valide rien : il redirige vers l'écran de paiement d'un parcours existant.
"""
from urllib.parse import quote

import frappe
from frappe.rate_limiter import rate_limit

from openlab_academy.application.paiements import PaiementIndisponible
from openlab_academy.entrypoints import paiement

HEURE = 3600
LIMITE_PAR_ADRESSE = 600  # requêtes par heure et par adresse IP, pour les points ouverts aux visiteurs


def _consigner(titre: str, transaction: str, motif: str) -> None:
    frappe.log_error(titre, f"{motif} (transaction {transaction[:64]!r})")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=LIMITE_PAR_ADRESSE, seconds=HEURE)
def notification_cinetpay() -> None:
    corps = dict(frappe.form_dict)
    transaction = str(corps.get("cpm_trans_id") or "")
    try:
        p = paiement.passerelle()
        if not transaction or not p.jeton_valide(corps, frappe.get_request_header("x-token")):
            _consigner("Notification CinetPay rejetée", transaction, "jeton, site ou transaction invalide")
            return
        paiement.confirmer_paiement(transaction, p)
    except PaiementIndisponible as e:  # message sans secret par construction
        frappe.db.rollback()
        _consigner("Notification CinetPay non traitée", transaction, str(e))
    except Exception as e:
        frappe.db.rollback()
        _consigner("Notification CinetPay non traitée", transaction, type(e).__name__)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=LIMITE_PAR_ADRESSE, seconds=HEURE)
def retour_cinetpay(cours: str | None = None) -> None:
    """Retour du navigateur après paiement (CinetPay peut y revenir en POST) : redirection interne seulement."""
    cible = "/espace"
    if isinstance(cours, str) and cours and frappe.db.exists("LMS Course", cours):
        cible = f"/espace/paiement/{quote(cours, safe='')}"
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = cible
