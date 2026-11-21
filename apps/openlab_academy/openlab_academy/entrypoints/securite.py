"""Commandes d'inscription et d'activation du second facteur, à lancer depuis le terminal.

Volontairement pas une API web. Le secret TOTP ne doit traverser ni une réponse HTTP, ni les
journaux du navigateur, ni l'historique d'une console : il s'affiche une fois, dans le terminal de
la personne qui l'enregistre, et nulle part ailleurs.

L'ordre est imposé par le code, pas par la mémoire de qui lance les commandes :

    1. inscrire_le_second_facteur  — affiche le QR à photographier, attend rien
    2. confirmer_le_second_facteur — vérifie un premier code et valide l'inscription
    3. activer_le_second_facteur   — refuse tant que l'étape 2 n'a pas abouti

En sens inverse, `eteindre_le_second_facteur` fonctionne toujours, même depuis une situation
cassée : on doit pouvoir rouvrir la porte sans avoir à toucher la base à la main.
"""
import frappe
import pyqrcode

from openlab_academy.domain.deuxieme_facteur import SecondFacteurInvalide
from openlab_academy.infrastructure import deuxieme_facteur_frappe as second

REGLAGES = second.REGLAGES


def _compte(utilisateur: str | None) -> str:
    compte = utilisateur or frappe.session.user
    if compte in ("Guest", None, ""):
        raise SystemExit("Précisez le compte : --kwargs \"{'utilisateur': 'vous@exemple.ci'}\"")
    if not frappe.db.exists("User", compte):
        raise SystemExit(f"Compte « {compte} » introuvable.")
    return compte


def inscrire_le_second_facteur(utilisateur: str | None = None) -> None:
    """Affiche le QR à photographier avec une application d'authentification.

    Rien n'est activé ici, et rien n'est encore considéré comme inscrit : tant que le code n'a pas
    été vérifié, le compte reste dans l'état où il était.
    """
    compte = _compte(utilisateur)
    lien = second.lien_d_inscription(compte)
    print(f"\nSecond facteur — inscription de {compte}\n")
    print(pyqrcode.create(lien).terminal(quiet_zone=1))
    print("Photographiez ce QR avec votre application d'authentification, puis lancez :\n")
    print("  bench --site <votre-site> execute "
          "openlab_academy.entrypoints.securite.confirmer_le_second_facteur \\\n"
          f"    --kwargs \"{{'utilisateur': '{compte}', 'code': '123456'}}\"\n")
    print("Le secret n'est affiché que maintenant et ne sera pas réaffiché.\n")


def confirmer_le_second_facteur(code: str, utilisateur: str | None = None) -> None:
    """Vérifie un premier code et marque l'inscription comme faite."""
    compte = _compte(utilisateur)
    if not second.confirmer(compte, str(code)):
        raise SystemExit("Code refusé. Vérifiez l'heure de votre téléphone, puis réessayez "
                         "avec le code affiché à l'instant.")
    frappe.db.commit()
    print(f"\nSecond facteur inscrit pour {compte}. Vous pouvez maintenant l'activer :\n")
    print("  bench --site <votre-site> execute "
          "openlab_academy.entrypoints.securite.activer_le_second_facteur\n")


def activer_le_second_facteur(roles: str | None = None, methode: str | None = None) -> None:
    """Active le second facteur pour les rôles demandés, si quelqu'un peut encore entrer."""
    doc = frappe.get_single(REGLAGES)
    if roles:
        doc.db_set("roles_deuxieme_facteur", roles.replace(",", "\n"), update_modified=False)
    if methode:
        doc.db_set("methode_deuxieme_facteur", methode, update_modified=False)
    doc.db_set("deuxieme_facteur", 1, update_modified=False)
    try:
        demande = second.reglage()
        second.appliquer(demande)
    except SecondFacteurInvalide as e:
        frappe.db.set_single_value(REGLAGES, "deuxieme_facteur", 0)
        frappe.db.commit()
        raise SystemExit(f"Activation refusée : {e}")
    frappe.db.commit()
    print(f"\nSecond facteur actif pour : {', '.join(demande.roles)} (méthode {demande.methode}).")
    print(f"Comptes capables d'entrer : {', '.join(second.porteurs(demande.roles))}\n")


def eteindre_le_second_facteur() -> None:
    """Rouvre la porte. Fonctionne en toute circonstance, y compris si plus personne n'entre."""
    frappe.db.set_single_value(REGLAGES, "deuxieme_facteur", 0)
    frappe.db.set_value(second.SYSTEME, second.SYSTEME, "enable_two_factor_auth", 0)
    for role in frappe.get_all("Role", {"two_factor_auth": 1}, pluck="name", ignore_permissions=True):
        frappe.db.set_value("Role", role, "two_factor_auth", 0)
    frappe.db.commit()
    print("\nSecond facteur éteint. Les inscriptions déjà faites sont conservées.\n")
