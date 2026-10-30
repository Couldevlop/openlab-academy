"""Page publique /parcours-ferme/<cours> : destination d'un visiteur ou d'un apprenant devant un parcours fermé.

Le nom du parcours vient de l'URL : il n'est jamais interpolé dans une requête brute (lecture par nom exact) ni dans
du HTML non échappé (le gabarit applique `| e` : l'autoéchappement de Frappe est désactivé), et la page ne redirige
vers rien de fourni par le client.
"""
import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from openlab_academy.application.visibilite import CATALOGUE

no_cache = 1


def _fenetre(cours: str):
    """Dates de la cohorte publiée la plus récente qui porte le parcours, ou None."""
    lots = frappe.get_all("Batch Course", {"course": cours, "parenttype": "LMS Batch"}, pluck="parent")
    if not lots:
        return None
    trouvees = frappe.get_all("LMS Batch", {"name": ["in", lots], "published": 1},
                              ["start_date", "end_date"], order_by="start_date desc", limit=1)
    return trouvees[0] if trouvees else None


def _jjmmaaaa(d) -> str:
    return getdate(d).strftime("%d/%m/%Y")


def get_context(context) -> None:
    context.no_cache = 1
    context.catalogue = CATALOGUE
    context.titre = ""
    context.debut = context.fin = ""
    context.a_venir = False
    context.message = ""
    nom = frappe.form_dict.get("cours")
    titre = frappe.db.get_value("LMS Course", nom, "title") if isinstance(nom, str) and nom else None
    if not titre:
        return
    context.titre = titre
    fenetre = _fenetre(nom)
    if fenetre is None:
        return
    context.debut, context.fin = _jjmmaaaa(fenetre.start_date), _jjmmaaaa(fenetre.end_date)
    context.a_venir = getdate(fenetre.start_date) > getdate(nowdate())
    if context.a_venir:
        context.message = _("« {0} » ouvrira le {1}.").format(titre, context.debut)
    else:
        # littéral sur une ligne : l'extracteur du garde-fou de traductions ne suit pas les concaténations
        context.message = _("« {0} » était ouvert du {1} au {2}. Votre progression et votre certificat restent dans votre profil.").format(titre, context.debut, context.fin)  # noqa: E501
