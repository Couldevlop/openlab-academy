"""Écran « Inscrits et gratuités » d'un parcours : qui paie, à qui le parcours est offert, et la bascule.

Deux points d'entrée seulement, tous deux réservés à l'administrateur et à l'intendant : lire les inscrits d'un
parcours avec leur état, et basculer une personne d'un état à l'autre. Les droits sont vérifiés ici, jamais
dans l'écran : un appel direct à l'API passe par les mêmes contrôles.
"""
import frappe
from frappe import _

from openlab_academy.application.gratuites import AccorderGratuite, GratuiteReservee, RetirerGratuite
from openlab_academy.application.tableaux_paiement import LIBELLES_STATUT
from openlab_academy.domain.dossier_paiement import reste_du, statut
from openlab_academy.entrypoints.paiement import jour_courant
from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT, DepotDossiersFrappe
from openlab_academy.infrastructure.gratuites_frappe import GratuitesFrappe
from openlab_academy.infrastructure.journal_paiement_frappe import journaliser

ADMINISTRATEUR = "System Manager"
INTENDANT = "Intendant OpenLab"
ROLE_APPRENANT = "LMS Student"
LONGUEUR_MINIMALE = 12


def _mot_de_passe_tire() -> str:
    """Un mot de passe d'essai qui franchit une politique de robustesse exigeante.

    `frappe.generate_hash` ne rend que des caracteres hexadecimaux : long mais pauvre, il peut etre
    recale par un controle qui reclame plusieurs familles de caracteres, et la creation echouerait
    alors sans que personne n'ait rien demande de faible. On compose donc explicitement.
    """
    return frappe.generate_hash(length=14) + "-Ol9#"


def _habilite(utilisateur: str | None = None) -> bool:
    roles = set(frappe.get_roles(utilisateur or frappe.session.user))
    return bool({ADMINISTRATEUR, INTENDANT} & roles)


def _exiger_le_droit() -> None:
    if not _habilite():
        frappe.throw(_("Réservé à l'administrateur et à l'intendant."), frappe.PermissionError)


def _etat(depot: DepotDossiersFrappe, apprenant: str, cours: str, offert: bool) -> dict:
    """L'état est rendu lisible ici (les mêmes libellés que l'intendance) : l'écran n'a rien à traduire."""
    enregistre = depot.charger(apprenant, cours)
    if enregistre is None:
        return {"etat": _("Offert") if offert else _("Sans dossier"), "reste": 0}
    dossier = enregistre.dossier
    return {"etat": _(LIBELLES_STATUT[statut(dossier, jour_courant())]), "reste": reste_du(dossier),
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


@frappe.whitelist(methods=["POST"])
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


@frappe.whitelist(methods=["POST"])
def creer_apprenant(courriel: str, nom: str, prenom: str = "", mot_de_passe: str = "") -> dict:
    """Crée un compte apprenant utilisable tout de suite. Pour les tests utilisateurs.

    Frappe sait déjà créer un utilisateur dans son interface, mais le compte né ainsi attend un
    courriel de bienvenue pour choisir son mot de passe — et les comptes d'envoi de production ne
    sont pas en service. Un compte d'essai doit donc naître actif, avec un mot de passe connu.

    **Rejouable, et sans jamais réinitialiser.** Sur un compte qui existe déjà, il est renvoyé tel
    quel : une réinitialisation silencieuse ferait perdre son accès à quelqu'un, et ce point
    d'entrée n'est pas un outil de dépannage de mot de passe.

    Le mot de passe n'est rendu que lorsqu'il a été tiré ici, et une seule fois : celui que
    l'administrateur a choisi, il le connaît déjà, et le renvoyer ne ferait que l'exposer une fois
    de plus — réponse d'API, journaux du navigateur, historique. Il n'est jamais journalisé.

    **La suspension des inscriptions publiques ne s'applique pas à ce chemin**, et c'est voulu :
    elle vit dans le cas d'usage du site (`inscrire_au_parcours`), que l'administration n'emprunte
    pas. Sans cela, aucun test utilisateur ne serait possible pendant la suspension.
    """
    _exiger_le_droit()
    adresse = (courriel or "").strip() if isinstance(courriel, str) else ""
    nom_de_famille = (nom or "").strip() if isinstance(nom, str) else ""
    if not adresse or not nom_de_famille:
        frappe.throw(_("Un compte demande une adresse électronique et un nom."),
                     frappe.ValidationError)
    if frappe.db.exists("User", adresse):
        return {"apprenant": adresse, "cree": False, "mot_de_passe": ""}

    tire = not (isinstance(mot_de_passe, str) and mot_de_passe.strip())
    secret = _mot_de_passe_tire() if tire else mot_de_passe.strip()
    # Le document applique la politique de robustesse du site — mais elle est desactivee par defaut
    # (`minimum_password_score` a zero), et « 123 » passerait. Ce plancher est donc le notre, tenu
    # ici : un compte d'essai ouvre une session sur le meme site que les autres.
    if len(secret) < LONGUEUR_MINIMALE:
        frappe.throw(_("Un mot de passe de moins de {0} caracteres est refuse.").format(
            LONGUEUR_MINIMALE), frappe.ValidationError)
    # Le mot de passe passe par le document, et non par une ecriture directe : seul ce chemin
    # declenche la politique de robustesse du site. Un compte d'essai ouvre une session comme les
    # autres ; il ne doit pas etre la seule porte par laquelle « 123 » devient un mot de passe.
    compte = frappe.get_doc({
        "doctype": "User", "email": adresse, "first_name": (prenom or "").strip() or nom_de_famille,
        "last_name": nom_de_famille if (prenom or "").strip() else "",
        "enabled": 1, "user_type": "Website User", "send_welcome_email": 0,
        "new_password": secret, "roles": [{"role": ROLE_APPRENANT}]})
    compte.flags.no_welcome_mail = True
    # `ignore_permissions` est delibere : l'intendant n'a pas le droit de creer un utilisateur dans
    # le bureau, et ne doit pas l'avoir. Le droit est tenu plus haut par `_exiger_le_droit`, et le
    # role accorde est ecrit en dur — ce chemin ne peut donc pas servir a s'elever. Qui a cree le
    # compte reste lisible : Frappe inscrit l'auteur dans `owner`.
    compte.insert(ignore_permissions=True)
    return {"apprenant": adresse, "cree": True, "mot_de_passe": secret if tire else ""}


@frappe.whitelist(methods=["POST"])
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
