"""Points d'accroche de l'évaluation : rendu d'un devoir LMS, étapes en tâche de fond, échéances horaires.

Rien ne bloque : une erreur interne est consignée, ses écritures partielles sont annulées (point de sauvegarde),
et la copie reste à son étape, que l'échéance fera avancer.
"""
from collections.abc import Callable

import frappe
from frappe.utils import now_datetime

from openlab_academy.application.chaine import SYSTEME, TACHES, FaireAvancer, TraiterEcheances
from openlab_academy.application.corriger import LibererNote
from openlab_academy.application.controler import ControlerCopie, consigner_indisponibilite
from openlab_academy.application.pre_corriger import PreCorriger
from openlab_academy.application.soumettre_copie import SoumettreCopie
from openlab_academy.domain.reglages_evaluation import Etape
from openlab_academy.infrastructure import journal_frappe, reglages_evaluation_frappe
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe, cours_evalue
from openlab_academy.infrastructure.depot_relectures_frappe import DepotRelecturesFrappe
from openlab_academy.infrastructure.controles import ControleurDepots
from openlab_academy.infrastructure.correcteur_ia import CorrecteurCompatibleOpenAI
from openlab_academy.infrastructure.instantane_depot import BUDGET_TACHE_S, InstantaneDepot

CHAMPS = ("name", "assignment", "member", "type", "answer", "assignment_attachment")
POINT = "openlab_rendu"
POINT_ETAPE = "openlab_etape"
MARGE_S = 60  # la tâche survit au délai de l'appel au modèle : c'est lui qui expire, proprement


def isoler(action: Callable[[], None]) -> None:
    """Exécute une action automatique ; en cas d'erreur, l'annule seule et la consigne."""
    frappe.db.savepoint(POINT_ETAPE)
    try:
        action()
    except Exception:
        frappe.db.rollback(save_point=POINT_ETAPE)
        frappe.log_error(title="openlab_academy : étape automatique en échec", message=frappe.get_traceback())


def unite(action: Callable[[], None]) -> None:
    """Tâche horaire : chaque copie ou relecture est sa propre transaction. Une erreur (y compris un
    interblocage, qui annule toute la transaction) ne coûte que cet élément, consigné ; les autres sont validés."""
    try:
        action()
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        frappe.log_error(title="openlab_academy : échéance non traitée", message=frappe.get_traceback())
        frappe.db.commit()


def file(tache: str, copie_id: str) -> None:
    """Met une étape en tâche de fond ; une file indisponible ne bloque pas : l'échéance prendra le relais."""
    if tache not in TACHES.values():
        raise ValueError(f"tâche inconnue : {tache}")
    try:
        options = {}
        if tache == TACHES[Etape.IA]:  # plusieurs minutes sur CPU : file longue, délai réglé dans la console
            delai_s = reglages_evaluation_frappe.charger().ia.delai_minutes * 60
            options = {"queue": "long", "timeout": delai_s + MARGE_S}
        frappe.enqueue(f"{__name__}.{tache}", copie_id=copie_id, enqueue_after_commit=True, **options)
    except Exception:
        frappe.log_error(title="openlab_academy : tâche non mise en file", message=frappe.get_traceback())


def avanceur() -> FaireAvancer:
    return FaireAvancer(DepotCopiesFrappe(), DepotRelecturesFrappe(), reglages_evaluation_frappe.SourceReglagesFrappe(),
                        now_datetime, file, journal_frappe.journaliser)


def notifier(destinataire: str, message: str) -> None:
    """Alerte dans l'espace de l'apprenant (journal des notifications Frappe)."""
    frappe.get_doc({"doctype": "Notification Log", "for_user": destinataire, "type": "Alert",
                    "subject": message, "email_content": message}).insert(ignore_permissions=True)


def _executer(copie_id: str, etape: Etape, libelle: str, construire: Callable[[], object]) -> None:
    """Lecture de la console et des secrets comprise : rien de ce qui précède le cas d'usage ne s'échappe de la tâche."""
    try:
        cas = construire()
    except Exception as erreur:
        consigner_indisponibilite(avanceur(), journal_frappe.journaliser, copie_id, etape, libelle, erreur)
        return
    cas.executer(copie_id)


def controler(copie_id: str) -> None:
    """Contrôles automatiques : un échec bloquant renvoie la copie, un hébergeur indisponible la laisse avancer.
    Un rendu en URL sans instantané (hébergeur injoignable au rendu) est photographié ici, avec plus de temps."""
    def construire():
        reglages, jeton = reglages_evaluation_frappe.charger(), reglages_evaluation_frappe.jeton_depots()
        instantane = InstantaneDepot(reglages.hotes_depots, reglages.ia.plafond_caracteres, jeton=jeton,
                                     budget_s=BUDGET_TACHE_S)
        return ControlerCopie(DepotCopiesFrappe(), ControleurDepots(reglages, jeton=jeton), avanceur(),
                              journal_frappe.journaliser, notifier, instantane)
    _executer(copie_id, Etape.CONTROLES, "contrôles non disponibles", construire)


def pre_corriger(copie_id: str) -> None:
    """Pré-correction par le modèle souverain réglé dans la console ; une panne laisse la copie avancer."""
    def construire():
        reglages = reglages_evaluation_frappe.charger()
        correcteur = CorrecteurCompatibleOpenAI(reglages.ia.url, reglages_evaluation_frappe.cle_ia(),
                                                reglages.ia.delai_minutes * 60)
        return PreCorriger(DepotCopiesFrappe(), correcteur, reglages, avanceur(), journal_frappe.journaliser)
    _executer(copie_id, Etape.IA, "pré-correction non disponible", construire)


def traiter_echeances() -> None:
    """Tâche horaire : applique l'action réglée à chaque étape et relecture échue, puis libère les notes dont
    le gating est tombé (dispense, relectures faites ou retirées)."""
    TraiterEcheances(DepotCopiesFrappe(), DepotRelecturesFrappe(), reglages_evaluation_frappe.SourceReglagesFrappe(),
                     avanceur(), now_datetime, journal_frappe.journaliser, unite, notifier).executer()
    cas = liberateur()
    for copie_id in DepotCopiesFrappe().copies_differees():
        unite(lambda copie_id=copie_id: cas.executer(copie_id))


def liberateur() -> LibererNote:
    return LibererNote(DepotCopiesFrappe(), DepotRelecturesFrappe(), avanceur().chaine, journal_frappe.journaliser,
                       notifier)


def liberer_notes(apprenant: str) -> None:
    """Tâche de fond, après la relecture d'un apprenant : ses notes différées sortent si plus rien n'est dû.
    Hors de la transaction de la relecture ; chaque copie est sa propre transaction (`unite`), validée aussitôt :
    son verrou est relâché et une libération concurrente (échéancier) relit `lms_differe` déjà remis à zéro."""
    cas = liberateur()
    for copie_id in DepotCopiesFrappe().copies_differees(apprenant):
        unite(lambda copie_id=copie_id: cas.executer(copie_id))


def liberer_plus_tard(apprenant: str) -> None:
    try:
        frappe.enqueue(f"{__name__}.liberer_notes", apprenant=apprenant, enqueue_after_commit=True)
    except Exception:  # l'échéancier horaire prendra le relais
        frappe.log_error(title="openlab_academy : libération non mise en file", message=frappe.get_traceback())


def soumettre(soumission: dict) -> str | None:
    reglages = reglages_evaluation_frappe.charger()
    instantane = InstantaneDepot(reglages.hotes_depots, reglages.ia.plafond_caracteres,
                                 jeton=reglages_evaluation_frappe.jeton_depots())
    return SoumettreCopie(DepotCopiesFrappe(), instantane, reglages, now_datetime,
                          reglages_evaluation_frappe.surcharges, journal_frappe.journaliser,
                          lambda copie_id: isoler(lambda: avanceur().demarrer(copie_id))).executer(soumission)


def rendu(doc, method=None) -> None:
    soumission = {champ: doc.get(champ) for champ in CHAMPS}
    frappe.db.savepoint(POINT)
    try:
        copie = soumettre(soumission)
        if copie is None and method != "on_update" and cours_evalue(soumission["assignment"]):
            frappe.log_error(title="openlab_academy : exercice sans grille",
                             message=f"Le devoir {soumission['assignment']} n'a pas de grille OpenLab : "
                                     f"la soumission {soumission['name']} n'a pas de copie.")
    except Exception:
        frappe.db.rollback(save_point=POINT)
        frappe.log_error(title="openlab_academy : copie non créée", message=frappe.get_traceback())
