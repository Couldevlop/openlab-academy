"""Écran « Inscrits et gratuités » d'un parcours : qui paie, à qui le parcours est offert, et la bascule.

Deux points d'entrée seulement, tous deux réservés à l'administrateur et à l'intendant : lire les inscrits d'un
parcours avec leur état, et basculer une personne d'un état à l'autre. Les droits sont vérifiés ici, jamais
dans l'écran : un appel direct à l'API passe par les mêmes contrôles.
"""
import frappe
from frappe import _

from openlab_academy.application.gratuites import AccorderGratuite, GratuiteReservee, RetirerGratuite
from openlab_academy.domain.dossier_paiement import reste_du, statut
from openlab_academy.entrypoints.paiement import jour_courant
from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT, DepotDossiersFrappe
from openlab_academy.infrastructure.gratuites_frappe import GratuitesFrappe
from openlab_academy.infrastructure.journal_paiement_frappe import journaliser

ADMINISTRATEUR = "System Manager"
INTENDANT = "Intendant OpenLab"


def _habilite(utilisateur: str | None = None) -> bool:
    roles = set(frappe.get_roles(utilisateur or frappe.session.user))
    return bool({ADMINISTRATEUR, INTENDANT} & roles)


def _exiger_le_droit() -> None:
    if not _habilite():
        frappe.throw(_("Réservé à l'administrateur et à l'intendant."), frappe.PermissionError)


def _etat(depot: DepotDossiersFrappe, apprenant: str, cours: str, offert: bool) -> dict:
    enregistre = depot.charger(apprenant, cours)
    if enregistre is None:
        return {"etat": "offert" if offert else "sans dossier", "reste": 0}
    dossier = enregistre.dossier
    return {"etat": statut(dossier, jour_courant()).value, "reste": reste_du(dossier),
            "dossier": enregistre.nom}


@frappe.whitelist()
def inscrits(cours: str) -> dict:
    """Inscrits du parcours, plus les personnes à qui il est offert sans être encore inscrites."""
    _exiger_le_droit()
    gratuites, depot = GratuitesFrappe(), DepotDossiersFrappe()
    offerts = set(gratuites.apprenants(cours))
    membres = set(frappe.get_all("LMS Enrollment", {"course": cours}, pluck="member")) | offerts
    noms = {u.name: (u.full_name or u.name)
            for u in frappe.get_all("User", {"name": ["in", list(membres) or [""]]}, ["name", "full_name"])}
    lignes = [{"apprenant": membre, "nom": noms.get(membre, membre), "offert": membre in offerts,
               "inscrit": bool(frappe.db.exists("LMS Enrollment", {"course": cours, "member": membre})),
               **_etat(depot, membre, cours, membre in offerts)}
              for membre in sorted(membres)]
    return {"gratuit_pour_tous": bool(frappe.db.get_value("LMS Course", cours, CHAMP_GRATUIT)),
            "lignes": lignes}


@frappe.whitelist()
def inscrire(cours: str, apprenant: str) -> dict:
    """Inscrit une personne à qui le parcours est offert.

    Le LMS ferme l'auto-inscription des parcours payants (« self-learning disabled ») : l'inscription part donc
    d'ici, à la demande de l'administrateur ou de l'intendant. Elle reste une inscription complète — le dossier
    naît dans la foulée, tarif du jour figé, puis se dispense."""
    _exiger_le_droit()
    if not GratuitesFrappe().accordee(apprenant, cours):
        frappe.throw(_("Ce parcours n'est pas offert à cette personne : offrez-le d'abord."),
                     frappe.ValidationError)
    if not frappe.db.exists("LMS Enrollment", {"course": cours, "member": apprenant}):
        frappe.get_doc({"doctype": "LMS Enrollment", "course": cours, "member": apprenant}).insert(
            ignore_permissions=True)
    return inscrits(cours)


@frappe.whitelist()
def basculer(cours: str, apprenant: str, offert: int | str, motif: str = "") -> dict:
    """Offre le parcours à cet apprenant, ou le lui retire. Rejouable : l'état demandé est l'état obtenu."""
    _exiger_le_droit()
    if not frappe.db.exists("LMS Course", cours) or not frappe.db.exists("User", apprenant):
        frappe.throw(_("Parcours ou apprenant introuvable."), frappe.ValidationError)
    cas = AccorderGratuite if frappe.utils.cint(offert) else RetirerGratuite
    try:
        change = cas(GratuitesFrappe(), DepotDossiersFrappe(), journaliser, jour_courant).executer(
            frappe.session.user, apprenant, cours, habilite=True, motif=motif)
    except GratuiteReservee as e:
        frappe.throw(str(e), frappe.PermissionError)
    return {"change": change, **inscrits(cours)}
