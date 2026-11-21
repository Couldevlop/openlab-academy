"""Points d'API du site public : l'offre d'un parcours, et l'inscription.

`offre` est une lecture, ouverte aux visiteurs sans compte : c'est tout l'intérêt d'une façade — montrer
le prix et les dates à qui hésite encore. Elle n'écrit rien, et ne dit « déjà inscrit » qu'à propos de
l'utilisateur de la session.

`inscrire` écrit, et exige donc une session, un POST et le jeton CSRF que Frappe réclame de lui-même.
**L'apprenant inscrit est toujours celui de la session**, jamais un paramètre : sans cela, n'importe qui
inscrirait n'importe qui. Et la cohorte n'est pas davantage reçue — le cas d'usage la choisit, et sa
signature ne laisse aucune place pour en passer une.

Le nom du parcours vient du client : c'est la seule valeur qu'il fournit. Il n'est jamais interpolé dans
une requête brute (lecture par nom exact), et un parcours non publié est traité comme inexistant — rien
d'observable ne doit distinguer « en préparation » de « n'existe pas ».
"""
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from openlab_academy.application.inscrire_au_parcours import InscriptionImpossible, InscrireAuParcours
from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.depot_dossiers_frappe import (ParcoursGratuitsFrappe,
                                                                  ReglagesPaiementFrappe)
from openlab_academy.infrastructure.inscriptions_frappe import (CohortesPubliquesFrappe, InscripteurFrappe,
                                                                ReglagesInscriptionFrappe,
                                                                TarifsPublicsFrappe)

HEURE = 60 * 60
LIMITE_LECTURE = 240      # la page en fait un appel ; large, mais pas une porte ouverte au balayage
LIMITE_INSCRIPTION = 20   # s'inscrire vingt fois en une heure n'a pas de sens honnête


def _usage() -> InscrireAuParcours:
    return InscrireAuParcours(
        cohortes=CohortesPubliquesFrappe(),
        inscripteur=InscripteurFrappe(),
        gratuits=ParcoursGratuitsFrappe(),
        tarifs=TarifsPublicsFrappe(),
        reglages=ReglagesInscriptionFrappe(ReglagesPaiementFrappe()),
        aujourd_hui=frappe.utils.getdate)


def parcours_publie(nom) -> str:
    """Le parcours demandé, s'il existe, s'il est publié, et si ce visiteur a le droit de le voir.

    Les trois conditions se valent : un parcours non publié, ou masqué par la phase de lancement, ou
    fermé, est traité comme inexistant. Le distinguer apprendrait à un visiteur qu'un parcours se
    prépare, son nom avec, et laisserait lire son prix et ses dates — ce que `cours_refuses_courants`
    refuse partout ailleurs.

    C'est ici, et non dans les pages, que le filtre doit vivre : l'API est la porte la plus exposée, et
    une page qui filtrerait de son côté finirait par diverger de l'API qui ne le ferait pas.
    """
    if not isinstance(nom, str) or not nom:
        return ""
    if not frappe.db.get_value("LMS Course", nom, "published"):
        return ""
    return "" if nom in lms.cours_refuses_courants() else nom


def _apprenant() -> str:
    """L'utilisateur de la session, ou rien s'il s'agit d'un visiteur. Jamais un paramètre."""
    utilisateur = frappe.session.user
    return "" if utilisateur in ("Guest", None) else utilisateur


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=LIMITE_LECTURE, seconds=HEURE)
def offre(parcours: str) -> dict:
    """Ce que la page du parcours montre. Une lecture : aucune écriture, pour personne."""
    cours = parcours_publie(parcours)
    if not cours:
        frappe.throw(_("Ce parcours n'existe pas."), frappe.DoesNotExistError)
    return _usage().offre(cours, _apprenant()).en_dict()


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=LIMITE_INSCRIPTION, seconds=HEURE)
def inscrire(parcours: str) -> dict:
    """Inscrit l'utilisateur de la session au parcours, et dit où aller ensuite.

    Les refus du domaine (`InscriptionImpossible`) et ceux que les `doc_events` lèvent en chemin
    (`ValidationError` : inscription tardive, tarif absent, règle de cohorte) remontent tous en message
    lisible. Le visiteur doit comprendre pourquoi ; il n'a pas à lire une trace.
    """
    cours = parcours_publie(parcours)
    if not cours:
        frappe.throw(_("Ce parcours n'existe pas."), frappe.DoesNotExistError)
    try:
        return {"destination": _usage().executer(cours, _apprenant())}
    except InscriptionImpossible as refus:
        frappe.throw(str(refus), frappe.ValidationError)
