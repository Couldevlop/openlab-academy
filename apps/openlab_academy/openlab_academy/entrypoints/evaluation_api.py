"""Points d'API de l'évaluation, appelés par les écrans de relecture, de retour et de correction.

OWASP A01 : chaque point refuse le visiteur et vérifie l'accès côté serveur, dans le cas d'usage, avant toute
lecture de la ressource ; une ressource inexistante est refusée comme une ressource d'autrui (403). Les écritures
sont limitées en débit. Les textes des apprenants et de l'IA sont renvoyés en texte brut : l'écran les échappe.
"""
import json
import time
from collections.abc import Callable
from functools import wraps

import frappe
from frappe.utils import cint, get_datetime, now_datetime

from openlab_academy.application.corriger import (
    Acces, AccesRefuse, ConsulterCorrection, CorrectionRefusee, CorrigerCopie, GererDelegations, PublierNote,
    ValiderLot, fiabilite)
from openlab_academy.application.pairs import EnregistrerRelecture, RelectureRefusee
from openlab_academy.application.retours import AutoEvaluer, ConsulterRelectures, ConsulterRetour
from openlab_academy.domain.delegation import Delegation
from openlab_academy.entrypoints import evaluation
from openlab_academy.infrastructure import journal_frappe, reglages_evaluation_frappe
from openlab_academy.infrastructure.depot_copies_frappe import INSTRUCTEUR, DepotCopiesFrappe
from openlab_academy.infrastructure.depot_relectures_frappe import DepotRelecturesFrappe

HEURE = 3600
LOT_MAX = 200
LIMITES = {  # requêtes par heure et par utilisateur
    "enregistrer_relecture": 60, "enregistrer_auto_evaluation": 30, "corriger": 600, "valider_lot": 600,
    "publier": 600, "deleguer": 30, "revoquer": 30, "file_correction": 300,
}
SUPERVISEURS = {"System Manager", reglages_evaluation_frappe.ROLE}
CORRECTEURS_LMS = {"Moderator", "Course Creator", "Batch Evaluator"}


def _api(fn: Callable) -> Callable:
    """Visiteur refusé ; refus d'accès -> 403, saisie invalide -> erreur de validation."""
    @wraps(fn)
    def appel(*args, **kwargs):
        if frappe.session.user == "Guest":
            frappe.throw("Connexion requise.", frappe.PermissionError)
        try:
            return fn(*args, **kwargs)
        except AccesRefuse as e:
            frappe.throw(str(e), frappe.PermissionError)
        except (CorrectionRefusee, RelectureRefusee) as e:
            frappe.throw(str(e), frappe.ValidationError)
    return appel


def cle_debit(nom: str, utilisateur: str) -> str:
    """Compteur à fenêtre fixe d'une heure, par point d'API et par utilisateur (pas par adresse)."""
    return frappe.cache.make_key(f"openlab_academy:debit:{nom}:{utilisateur}:{int(time.time() // HEURE)}")


def _limite(nom: str) -> Callable:
    """Limitation de débit par utilisateur, appliquée aux requêtes HTTP ; au-delà -> 429."""
    def decorer(fn: Callable) -> Callable:
        @wraps(fn)
        def appel(*args, **kwargs):
            if getattr(frappe.local, "request", None):
                cle = cle_debit(nom, frappe.session.user)
                compte = frappe.cache.incrby(cle, 1)
                if compte == 1:
                    frappe.cache.expire(cle, HEURE)
                if compte > LIMITES[nom]:
                    frappe.throw("Trop de requêtes : réessayez plus tard.", frappe.TooManyRequestsError)
            return fn(*args, **kwargs)
        return appel
    return decorer


def _json(valeur, attendu: type):
    """Paramètre JSON (chaîne d'une requête HTTP) ou déjà décodé (appel direct)."""
    if isinstance(valeur, str):
        try:
            valeur = json.loads(valeur)
        except ValueError:
            raise CorrectionRefusee("paramètre JSON invalide") from None
    if valeur is not None and not isinstance(valeur, attendu):
        raise CorrectionRefusee("paramètre JSON invalide")
    return valeur


def _moi() -> str:
    return frappe.session.user


def _roles(utilisateur: str) -> set[str]:
    return set(frappe.get_roles(utilisateur))


def _administrateur(utilisateur: str) -> bool:
    return "System Manager" in _roles(utilisateur)


def _superviseur(utilisateur: str) -> bool:
    return bool(SUPERVISEURS & _roles(utilisateur))


def _habilite(utilisateur: str) -> bool:
    """Personne habilitée à corriger : superviseur, rôle LMS de correction ou formateur d'un cours ou d'un lot."""
    return (_superviseur(utilisateur) or bool(CORRECTEURS_LMS & _roles(utilisateur))
            or bool(frappe.db.exists(INSTRUCTEUR, {"instructor": utilisateur})))


def _depot() -> DepotCopiesFrappe:
    return DepotCopiesFrappe()


def _copie(depot: DepotCopiesFrappe, copie: str) -> str:
    if not depot.existe(copie):
        raise AccesRefuse("copie introuvable")
    return copie


def _acces(depot: DepotCopiesFrappe) -> Acces:
    return Acces(depot, reglages_evaluation_frappe.delegations, now_datetime, _administrateur)


def _seuil() -> float:
    return reglages_evaluation_frappe.charger().ia.seuil_confiance


def _publier(depot: DepotCopiesFrappe) -> PublierNote:
    return PublierNote(depot, DepotRelecturesFrappe(), _acces(depot), evaluation.avanceur(),
                       journal_frappe.journaliser, evaluation.notifier)


# --- apprenant : relectures, auto-évaluation, retour ------------------------------------------------------
@frappe.whitelist(methods=["GET"])
@_api
def mes_relectures() -> list[dict]:
    return ConsulterRelectures(_depot(), DepotRelecturesFrappe()).mes_relectures(_moi())


@frappe.whitelist(methods=["GET"])
@_api
def relecture(relecture_id: str) -> dict:
    return ConsulterRelectures(_depot(), DepotRelecturesFrappe()).relecture(_moi(), relecture_id)


@frappe.whitelist(methods=["POST"])
@_api
@_limite("enregistrer_relecture")
def enregistrer_relecture(relecture_id: str, niveaux: dict | str, commentaires: dict | str) -> None:
    relectures = DepotRelecturesFrappe()
    r = relectures.relecture(relecture_id)
    if r is None or r.relecteur != _moi():
        raise AccesRefuse("relecture non attribuée")
    EnregistrerRelecture(_depot(), relectures, evaluation.avanceur(), journal_frappe.journaliser).executer(
        _moi(), relecture_id, _json(niveaux, dict), _json(commentaires, dict) or {})
    evaluation.liberer_plus_tard(_moi())  # sa propre note, différée par le gating, peut sortir


@frappe.whitelist(methods=["GET"])
@_api
def mon_auto_evaluation(exercice: str) -> dict:
    return AutoEvaluer(_depot()).consulter(_moi(), exercice)


@frappe.whitelist(methods=["POST"])
@_api
@_limite("enregistrer_auto_evaluation")
def enregistrer_auto_evaluation(exercice: str, niveaux: dict | str) -> None:
    AutoEvaluer(_depot()).enregistrer(_moi(), exercice, _json(niveaux, dict))


@frappe.whitelist(methods=["GET"])
@_api
def mon_retour(copie: str) -> dict:
    depot = _depot()
    return ConsulterRetour(depot, DepotRelecturesFrappe(), evaluation.avanceur().chaine).executer(
        _moi(), _copie(depot, copie))


# --- correcteur : file, copie, correction, lots, publication ------------------------------------------------
@frappe.whitelist(methods=["GET"])
@_api
@_limite("file_correction")
def file_correction(exercice: str | None = None) -> dict:
    depot = _depot()
    return ConsulterCorrection(depot, _acces(depot), _seuil).file(_moi(), exercice or None)


@frappe.whitelist(methods=["GET"])
@_api
def copie_a_corriger(copie: str) -> dict:
    depot = _depot()
    return ConsulterCorrection(depot, _acces(depot), _seuil).copie(_moi(), _copie(depot, copie))


@frappe.whitelist(methods=["POST"])
@_api
@_limite("corriger")
def corriger(copie: str, niveaux: dict | str, commentaires: dict | str | None = None) -> None:
    depot = _depot()
    CorrigerCopie(depot, _acces(depot), evaluation.avanceur(), journal_frappe.journaliser).executer(
        _moi(), _copie(depot, copie), _json(niveaux, dict), _json(commentaires, dict))


@frappe.whitelist(methods=["POST"])
@_api
@_limite("valider_lot")
def valider_lot(copies: list | str, et_publier: int | str = 0) -> dict:
    depot = _depot()
    ids = _json(copies, list) or []
    if len(ids) > LOT_MAX or not all(isinstance(c, str) for c in ids):
        raise CorrectionRefusee(f"un lot compte au plus {LOT_MAX} identifiants de copies")
    ids = [_copie(depot, c) for c in ids]
    validees = ValiderLot(depot, _acces(depot), _seuil(), journal_frappe.journaliser).executer(_moi(), ids)
    publiees = []
    if cint(et_publier):
        cas = _publier(depot)
        for copie in validees:
            cas.executer(_moi(), copie)
            publiees.append(copie)
    return {"copies": validees, "publiees": publiees}


@frappe.whitelist(methods=["POST"])
@_api
@_limite("publier")
def publier(copie: str) -> dict:
    depot = _depot()
    return {"copie": copie, "note": _publier(depot).executer(_moi(), _copie(depot, copie))}


@frappe.whitelist(methods=["GET"])
@_api
def fiabilite_ia(exercice: str | None = None) -> dict[str, float]:
    """Écart moyen IA/formateur par critère sur les copies publiées : rapport de la console."""
    if not _superviseur(_moi()):
        raise AccesRefuse("rapport réservé au super administrateur et au responsable pédagogique")
    depot = _depot()
    return fiabilite(depot.propositions(c) for c in depot.copies_publiees(exercice or None))


# --- délégations ---------------------------------------------------------------------------------------
def _delegations() -> GererDelegations:
    return GererDelegations(reglages_evaluation_frappe.DepotDelegationsFrappe(), _habilite, _superviseur,
                            now_datetime, journal_frappe.journaliser)


@frappe.whitelist(methods=["POST"])
@_api
@_limite("deleguer")
def deleguer(delegataire: str, debut: str, fin: str, cohorte: str | None = None, exercice: str | None = None,
             titulaire: str | None = None) -> str:
    try:
        bornes = get_datetime(debut), get_datetime(fin)
    except Exception:
        bornes = None, None
    if None in bornes:
        raise CorrectionRefusee("dates de délégation invalides")
    d = Delegation(titulaire or _moi(), delegataire, *bornes, cohorte=cohorte or None, exercice=exercice or None)
    return _delegations().deleguer(_moi(), d)


@frappe.whitelist(methods=["POST"])
@_api
@_limite("revoquer")
def revoquer(delegation: str) -> None:
    _delegations().revoquer(_moi(), delegation)
