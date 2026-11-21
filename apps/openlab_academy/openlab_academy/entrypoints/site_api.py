"""Points d'API du site public : l'offre d'un parcours, et l'inscription.

`offre` est une lecture, ouverte aux visiteurs sans compte : c'est tout l'intérêt d'une façade — montrer
le prix et les dates à qui hésite encore. Elle n'écrit rien, et ne dit « déjà inscrit » qu'à propos de
l'utilisateur de la session.

`inscrire` écrit, et exige donc une session, un POST et le jeton CSRF que Frappe réclame de lui-même.
**L'apprenant inscrit est toujours celui de la session**, jamais un paramètre : sans cela, n'importe qui
inscrirait n'importe qui. Et la cohorte n'est pas davantage reçue — le cas d'usage la choisit, et sa
signature ne laisse aucune place pour en passer une.

Le nom du parcours vient du client : c'est la seule valeur qu'il fournit. Il n'est jamais interpolé dans
une requête brute (lecture par nom exact), et un parcours retiré du catalogue est traité comme
inexistant.

**Le site est une vitrine, et « en préparation » n'est plus un secret** : un parcours masqué par la
phase de lancement répond ici comme ailleurs — voir `parcours_du_catalogue`. Ce qui reste refusé n'est
pas l'existence du parcours, mais ce qui engagerait : son contenu de séance, et l'inscription elle-même
tant que `Reglages OpenLab Academy` ne l'a pas réouverte.
"""
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from openlab_academy.application.inscrire_au_parcours import InscriptionImpossible, InscrireAuParcours
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


def parcours_du_catalogue(nom) -> str:
    """Le parcours demandé, s'il existe et s'il est au catalogue public.

    **Le masquage de la phase de lancement ne s'applique plus ici, et c'est une décision.** Cette
    fonction traitait un parcours masqué comme inexistant, pour qu'un visiteur n'apprenne pas qu'un
    parcours se prépare. Le site est devenu une vitrine : l'existence et le programme des parcours à
    venir sont l'argument de vente, et un catalogue de neuf entrées dont huit sont cachées se lit
    comme un catalogue d'une entrée. La précaution protégeait un secret que nous ne gardons plus.

    Ce qui reste fermé, et que les tests exigent : le corps des séances, que la fiche ne sert jamais
    (elle n'affiche que des titres) ; l'accès à `/lms/courses/<nom>`, toujours gouverné par les
    règles du LMS ; et le masquage lui-même, qui continue de s'appliquer **dans le LMS** pour
    l'apprenant connecté — seule la façade publique s'en affranchit.

    **`published` reste l'interrupteur.** Le relever aussi aurait ressuscité les parcours que
    `lancement.retirer_parcours_echus` dépublie chaque nuit, et rendu public tout brouillon commencé
    dans l'administration. C'est le seul moyen qui reste de retirer une page du site.

    C'est ici, et non dans les pages, que le filtre doit vivre : l'API est la porte la plus exposée, et
    une page qui filtrerait de son côté finirait par diverger de l'API qui ne le ferait pas.
    """
    if not isinstance(nom, str) or not nom:
        return ""
    return nom if frappe.db.get_value("LMS Course", nom, "published") else ""


def _apprenant() -> str:
    """L'utilisateur de la session, ou rien s'il s'agit d'un visiteur. Jamais un paramètre."""
    utilisateur = frappe.session.user
    return "" if utilisateur in ("Guest", None) else utilisateur


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=LIMITE_LECTURE, seconds=HEURE)
def offre(parcours: str) -> dict:
    """Ce que la page du parcours montre. Une lecture : aucune écriture, pour personne."""
    cours = parcours_du_catalogue(parcours)
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
    cours = parcours_du_catalogue(parcours)
    if not cours:
        frappe.throw(_("Ce parcours n'existe pas."), frappe.DoesNotExistError)
    try:
        return {"destination": _usage().executer(cours, _apprenant())}
    except InscriptionImpossible as refus:
        frappe.throw(str(refus), frappe.ValidationError)
