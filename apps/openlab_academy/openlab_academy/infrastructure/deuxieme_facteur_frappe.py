"""Applique le second facteur dans Frappe : réglages du site, drapeau des rôles, inscription.

Frappe tient déjà tout le mécanisme TOTP. Ce module ne le réécrit pas : il traduit nos réglages en
réglages du site, et il ajoute le seul garde-fou qui manque — refuser d'activer tant que personne
n'a inscrit de second facteur. Sans lui, le code d'inscription part par courriel au premier accès,
et un site sans compte d'envoi en service reste fermé pour toujours.

L'inscription ne passe jamais par une réponse d'API ni par un journal : le secret est rendu à
l'appelant, qui est la personne devant son terminal, et nulle part ailleurs.
"""
import frappe
import pyotp

from openlab_academy.domain.deuxieme_facteur import (METHODE_PAR_DEFAUT, ROLES_PAR_DEFAUT, Reglage,
                                                     SecondFacteurInvalide, exiger_un_porteur,
                                                     methode_valide, roles_demandes)

REGLAGES = "Reglages OpenLab Academy"
SYSTEME = "System Settings"
# Marque posée par Frappe une fois qu'un compte a vérifié un premier code. Elle se lit par les
# accesseurs de Frappe et par eux seuls : c'est un défaut *global* rangé sous le parent « __2fa »,
# de clé « <compte>_otplogin », et non un défaut d'utilisateur. Lue autrement, elle répond vrai
# pour tout le monde — le garde-fou croirait alors tout le monde inscrit et ouvrirait l'activation
# qui ferme la porte. Passer par `frappe.twofactor` garantit qu'on lit la même chose que l'écran
# d'authentification, et non une marque parallèle qui dirait autre chose.
def _marque(utilisateur: str) -> str:
    return f"{utilisateur}_otplogin"


def _roles_connus() -> tuple[str, ...]:
    return tuple(frappe.get_all("Role", pluck="name", ignore_permissions=True))


def reglage() -> Reglage:
    """Ce que l'administration demande, lu et validé."""
    doc = frappe.get_single(REGLAGES)
    return Reglage(
        actif=bool(doc.get("deuxieme_facteur")),
        methode=methode_valide(doc.get("methode_deuxieme_facteur") or METHODE_PAR_DEFAUT),
        roles=roles_demandes(doc.get("roles_deuxieme_facteur") or "", _roles_connus()),
    )


def inscrit(utilisateur: str) -> bool:
    """Ce compte a-t-il déjà vérifié un premier code ?"""
    from frappe.twofactor import get_default
    return bool(get_default(_marque(utilisateur)))


def porteurs(roles: tuple[str, ...]) -> tuple[str, ...]:
    """Les comptes actifs qui tiennent l'un des rôles demandés et ont terminé leur inscription."""
    if not roles:
        return ()
    comptes = frappe.get_all("Has Role", {"role": ["in", list(roles)], "parenttype": "User"},
                             pluck="parent", ignore_permissions=True)
    actifs = set(frappe.get_all("User", {"name": ["in", list(set(comptes)) or [""]], "enabled": 1},
                                pluck="name", ignore_permissions=True))
    return tuple(sorted(c for c in actifs if inscrit(c)))


def secret(utilisateur: str) -> str:
    """Le secret TOTP du compte, créé au besoin. À ne rendre qu'à la personne elle-même."""
    from frappe.twofactor import get_otpsecret_for_
    return get_otpsecret_for_(utilisateur)


def lien_d_inscription(utilisateur: str) -> str:
    """L'URI `otpauth://` à présenter sous forme de QR. Contient le secret : jamais journalisée."""
    nom = frappe.db.get_single_value(SYSTEME, "otp_issuer_name") or "Openlab Academy"
    return pyotp.TOTP(secret(utilisateur)).provisioning_uri(utilisateur, issuer_name=nom)


def confirmer(utilisateur: str, code: str) -> bool:
    """Vérifie un premier code et marque l'inscription comme faite.

    C'est la vérification qui compte : sans elle on marquerait inscrit quelqu'un qui n'a rien
    enregistré, et le garde-fou d'activation laisserait passer une porte en réalité fermée.
    """
    if not pyotp.TOTP(secret(utilisateur)).verify((code or "").strip(), valid_window=1):
        return False
    from frappe.twofactor import set_default
    set_default(_marque(utilisateur), 1)
    return True


def oublier(utilisateur: str) -> None:
    """Efface l'inscription d'un compte : son prochain accès repassera par l'enrôlement."""
    from frappe.twofactor import clear_default
    clear_default(_marque(utilisateur))


def appliquer(demande: Reglage) -> None:
    """Traduit le réglage en configuration du site, après le garde-fou d'accès."""
    exiger_un_porteur(demande, porteurs(demande.roles))
    systeme = frappe.get_single(SYSTEME)
    systeme.enable_two_factor_auth = int(demande.actif)
    systeme.two_factor_method = demande.methode
    systeme.save(ignore_permissions=True)
    # Le drapeau est repris a zero a chaque passage : un role retire du reglage doit cesser d'etre
    # soumis, sinon la case decochee dans l'administration ne changerait rien pour lui.
    for role in frappe.get_all("Role", {"two_factor_auth": 1}, pluck="name", ignore_permissions=True):
        if role not in demande.roles:
            frappe.db.set_value("Role", role, "two_factor_auth", 0)
    for role in demande.roles:
        frappe.db.set_value("Role", role, "two_factor_auth", 1)


def preparer() -> None:
    """Installation et migration : pose les valeurs par défaut, puis applique ce qui est demandé.

    Une migration ne doit jamais fermer la porte : si le réglage demandé n'est pas tenable — plus
    aucun porteur, par exemple — on le laisse éteint et on le dit, plutôt que d'échouer la
    migration ou, pire, de verrouiller le site.
    """
    doc = frappe.get_single(REGLAGES)
    if doc.get("roles_deuxieme_facteur") is None or not str(doc.get("roles_deuxieme_facteur")).strip():
        doc.db_set("roles_deuxieme_facteur", "\n".join(ROLES_PAR_DEFAUT), update_modified=False)
    if not doc.get("methode_deuxieme_facteur"):
        doc.db_set("methode_deuxieme_facteur", METHODE_PAR_DEFAUT, update_modified=False)
    try:
        appliquer(reglage())
    except SecondFacteurInvalide as e:
        frappe.db.set_value(SYSTEME, SYSTEME, "enable_two_factor_auth", 0)
        frappe.db.set_single_value(REGLAGES, "deuxieme_facteur", 0)
        print(f"Second facteur laissé éteint : {e}")
