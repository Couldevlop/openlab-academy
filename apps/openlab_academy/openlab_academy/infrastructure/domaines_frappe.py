"""Adaptateur : la table des domaines, telle que l'administration l'a remplie.

La liste n'est pas dans le code, elle est en base — c'est tout l'objet de ce fichier. Les six
familles livrées à l'installation ne sont qu'une semence : ouvrir une filière se fait depuis
l'administration, sans livraison.
"""
import frappe

from openlab_academy.domain.domaine import (DOMAINES_PAR_DEFAUT, Domaine, DomaineInconnu,
                                            TeinteIllisible, normaliser, valider)
from openlab_academy.infrastructure.champs_frappe import champ_personnalise

DOCTYPE = "Domaine OpenLab"
PARCOURS = "LMS Course"
CHAMP = "ol_domaine"  # champ personnalisé du parcours : lien vers la famille


def _teinte_sure(teinte: str) -> str:
    """La teinte si elle est bien une couleur, rien sinon.

    Le formulaire la valide, mais une ecriture directe en base — un correctif, un import, un test —
    ne passe pas par `validate`. Or cette valeur part dans un attribut `style` d'une page publique.
    Une teinte invalide fait donc retomber la carte sur la couleur neutre de la charte plutot que de
    porter n'importe quoi jusqu'au navigateur. Les gabarits l'echappent en plus : l'app n'a pas
    l'autoechappement de Jinja.
    """
    try:
        return normaliser(teinte)
    except TeinteIllisible:
        return ""


def tous() -> tuple[Domaine, ...]:
    """Les domaines configurés, dans l'ordre choisi par l'administration."""
    lignes = frappe.get_all(DOCTYPE, fields=["cle", "libelle", "teinte"], order_by="rang asc, cle asc",
                            ignore_permissions=True)
    return tuple(Domaine(ligne["cle"], ligne["libelle"], _teinte_sure(ligne["teinte"]))
                 for ligne in lignes)


def cles() -> tuple[str, ...]:
    return tuple(d.cle for d in tous())


def par_cle() -> dict[str, Domaine]:
    return {d.cle: d for d in tous()}


def preparer() -> None:
    """Pose la semence si la table est vide, et ne touche à rien sinon.

    Une migration ne doit pas rétablir un domaine que l'équipe a supprimé, ni écraser une teinte
    qu'elle a choisie. Le test de vacuité est donc global, et non clé par clé.
    """
    if frappe.db.count(DOCTYPE):
        return
    for rang, domaine in enumerate(DOMAINES_PAR_DEFAUT):
        frappe.get_doc({"doctype": DOCTYPE, "cle": domaine.cle, "libelle": domaine.libelle,
                        "teinte": domaine.teinte, "rang": rang}).insert(ignore_permissions=True)


def preparer_champ() -> None:
    """Le champ du parcours qui porte sa famille.

    Un lien vers notre table, et non la catégorie du LMS : la catégorie est du texte libre, si bien
    qu'un libellé renommé dans l'administration laisserait les parcours accrochés à l'ancien nom.
    Un lien suit le renommage tout seul, et une famille encore utilisée ne peut pas être supprimée
    par mégarde — Frappe refuse.
    """
    champ_personnalise(PARCOURS, CHAMP, {
        "fieldtype": "Link", "options": DOCTYPE, "label": "Domaine", "insert_after": "category",
        "description": "Famille du parcours. Elle donne sa teinte à la carte du catalogue public."})


def du_parcours(cours: str) -> Domaine | None:
    """La famille d'un parcours, ou rien s'il n'en porte pas."""
    cle = frappe.db.get_value(PARCOURS, cours, CHAMP)
    return par_cle().get(cle) if cle else None


def exiger(cle: str) -> str:
    """La clé si la table la connaît, sinon une erreur qui nomme les familles existantes.

    Appelée à la publication d'un parcours : une faute de frappe dans un fichier doit se voir à ce
    moment-là, pas se traduire par une carte grise sur le site.
    """
    return valider(cle, cles())


__all__ = ["DOCTYPE", "CHAMP", "tous", "cles", "par_cle", "preparer", "preparer_champ", "du_parcours",
           "exiger", "DomaineInconnu"]
