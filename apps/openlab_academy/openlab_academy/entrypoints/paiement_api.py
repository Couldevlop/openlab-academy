"""Points d'API du paiement : notification et retour CinetPay.

La notification est un appel serveur à serveur sans session (Guest) : Frappe ne lui demande pas de jeton CSRF, la
preuve d'origine est l'en-tête `x-token` (HMAC de la clé secrète), puis le statut et le montant sont toujours relus
auprès de CinetPay avant toute écriture. Elle répond 200 dans tous les cas (sinon CinetPay la rejoue) et consigne
les refus sans aucun secret. En cas d'erreur, seule la requête en cours est annulée : le paiement en attente, validé
lors de l'initiation, demeure. Le retour redirige vers l'écran de paiement d'un parcours existant ; pour l'apprenant
connecté, il revérifie d'abord ses paiements en attente sur ce parcours (notification perdue), sans jamais bloquer
la redirection.

Virements et délais : réservés à l'Intendant et à l'administrateur (vérifié côté serveur avant toute lecture),
en POST pour des agents connectés (Frappe exige alors le jeton CSRF) ; l'acteur journalisé est toujours l'utilisateur
de la session, jamais un paramètre.
"""
import re
from collections.abc import Callable
from datetime import date
from functools import wraps
from urllib.parse import quote

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import getdate

from openlab_academy.application.paiements import DossierAbsent, OperationRefusee, PaiementIndisponible
from openlab_academy.entrypoints import paiement

HEURE = 3600
LIMITE_PAR_ADRESSE = 600  # requêtes par heure et par adresse IP, pour les points ouverts aux visiteurs
LIMITE_AGENTS = 120  # saisies par heure et par adresse IP pour les points réservés aux agents
ROLES_AGENTS = frozenset({"System Manager", "Intendant OpenLab"})
_ENTIER = re.compile(r"[0-9]{1,12}")


def _consigner(titre: str, transaction: str, motif: str) -> None:
    frappe.log_error(titre, f"{motif} (transaction {transaction[:64]!r})")


def _reconcilier(utilisateur: str, cours: str) -> None:
    """Contrôle des paiements en attente au retour ; toute erreur est consignée sans secret, jamais propagée."""
    try:
        paiement.reconcilier_paiements(utilisateur, cours)
    except PaiementIndisponible as e:  # rien d'écrit pour le paiement en échec ; les confirmations faites restent
        frappe.log_error("Retour CinetPay : contrôle impossible", f"{e} (parcours {cours[:64]!r})")
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error("Retour CinetPay : contrôle impossible", f"{type(e).__name__} (parcours {cours[:64]!r})")
    frappe.local.flags.commit = True  # requête GET : Frappe ne valide sinon pas les écritures


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
        if frappe.session.user != "Guest":
            _reconcilier(frappe.session.user, cours)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = cible


# --- virements et délais ---------------------------------------------------------------------------------
def _api(fn: Callable) -> Callable:
    """Visiteur et rôles non habilités refusés (403) avant tout traitement ; saisie refusée -> erreur de validation."""
    @wraps(fn)
    def appel(*args, **kwargs):
        if frappe.session.user == "Guest" or not ROLES_AGENTS & set(frappe.get_roles(frappe.session.user)):
            frappe.throw("Accès réservé à l'intendant et à l'administrateur.", frappe.PermissionError)
        try:
            return fn(*args, **kwargs)
        except (OperationRefusee, DossierAbsent) as e:
            frappe.throw(str(e), frappe.ValidationError)
    return appel


def _entier(valeur):
    """Entier tel quel, ou chaîne de chiffres d'une requête HTTP ; toute autre valeur reste refusée par le cas d'usage."""
    if isinstance(valeur, str) and _ENTIER.fullmatch(valeur.strip()):
        return int(valeur)
    return valeur


def _jour(valeur) -> date | None:
    """Date ISO d'une requête ; None si absente ou illisible (refusée ensuite par le cas d'usage)."""
    try:
        return getdate(valeur) if isinstance(valeur, str) and valeur.strip() else None
    except Exception:
        return None


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=LIMITE_AGENTS, seconds=HEURE)
@_api
def enregistrer_virement(dossier: str, montant, reference: str, date_paiement: str, motif: str = "") -> None:
    paiement.enregistrer_virement(frappe.session.user, dossier, _entier(montant), reference,
                                  _jour(date_paiement), motif)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=LIMITE_AGENTS, seconds=HEURE)
@_api
def accorder_delai(dossier: str, jusqu_au: str, motif: str) -> None:
    paiement.accorder_delai(frappe.session.user, dossier, _jour(jusqu_au), motif)
