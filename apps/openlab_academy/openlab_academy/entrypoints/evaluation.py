"""Points d'accroche de l'évaluation : rendu d'un devoir LMS, étapes en tâche de fond, échéances horaires.

Rien ne bloque : une erreur interne est consignée, ses écritures partielles sont annulées (point de sauvegarde),
et la copie reste à son étape, que l'échéance fera avancer.
"""
from collections.abc import Callable

import frappe
from frappe.utils import now_datetime

from openlab_academy.application.chaine import SYSTEME, TACHES, FaireAvancer, TraiterEcheances
from openlab_academy.application.soumettre_copie import SoumettreCopie
from openlab_academy.domain.reglages_evaluation import Etape
from openlab_academy.infrastructure import journal_frappe, reglages_evaluation_frappe
from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe, cours_evalue
from openlab_academy.infrastructure.depot_relectures_frappe import DepotRelecturesFrappe
from openlab_academy.infrastructure.instantane_provisoire import InstantaneProvisoire

CHAMPS = ("name", "assignment", "member", "type", "answer", "assignment_attachment")
POINT = "openlab_rendu"
POINT_ETAPE = "openlab_etape"


def isoler(action: Callable[[], None]) -> None:
    """Exécute une action automatique ; en cas d'erreur, l'annule seule et la consigne."""
    frappe.db.savepoint(POINT_ETAPE)
    try:
        action()
    except Exception:
        frappe.db.rollback(save_point=POINT_ETAPE)
        frappe.log_error(title="openlab_academy : étape automatique en échec", message=frappe.get_traceback())


def file(tache: str, copie_id: str) -> None:
    """Met une étape en tâche de fond ; une file indisponible ne bloque pas : l'échéance prendra le relais."""
    if tache not in TACHES.values():
        raise ValueError(f"tâche inconnue : {tache}")
    try:
        frappe.enqueue(f"{__name__}.{tache}", copie_id=copie_id, enqueue_after_commit=True)
    except Exception:
        frappe.log_error(title="openlab_academy : tâche non mise en file", message=frappe.get_traceback())


def avanceur() -> FaireAvancer:
    return FaireAvancer(DepotCopiesFrappe(), DepotRelecturesFrappe(), reglages_evaluation_frappe.SourceReglagesFrappe(),
                        now_datetime, file, journal_frappe.journaliser)


def _non_disponible(copie_id: str, etape: Etape, libelle: str) -> None:
    """Consigne l'indisponibilité si le résultat est encore attendu ; n'avance que si l'étape est la courante."""
    avancer = avanceur()
    if not avancer.accepte_resultat(copie_id, etape):
        return  # signal périmé : la copie a quitté cette étape (ou est publiée, ou remplacée)
    journal_frappe.journaliser(copie_id, SYSTEME, libelle, {}, {"etape": etape.value})
    avancer.executer(copie_id, etape)


def notifier(destinataire: str, message: str) -> None:
    """Alerte dans l'espace de l'apprenant (journal des notifications Frappe)."""
    frappe.get_doc({"doctype": "Notification Log", "for_user": destinataire, "type": "Alert",
                    "subject": message, "email_content": message}).insert(ignore_permissions=True)


def controler(copie_id: str) -> None:
    """Contrôles automatiques : pas encore branchés, l'étape est marquée « non disponible » et la copie avance."""
    _non_disponible(copie_id, Etape.CONTROLES, "contrôles non disponibles")


def pre_corriger(copie_id: str) -> None:
    """Pré-correction : pas encore branchée, l'étape est marquée « non disponible » et la copie avance."""
    _non_disponible(copie_id, Etape.IA, "pré-correction non disponible")


def traiter_echeances() -> None:
    """Tâche horaire : applique l'action réglée à chaque étape et relecture échue."""
    TraiterEcheances(DepotCopiesFrappe(), DepotRelecturesFrappe(), reglages_evaluation_frappe.SourceReglagesFrappe(),
                     avanceur(), now_datetime, journal_frappe.journaliser, isoler, notifier).executer()


def soumettre(soumission: dict) -> str | None:
    return SoumettreCopie(DepotCopiesFrappe(), InstantaneProvisoire(), reglages_evaluation_frappe.charger(),
                          now_datetime, reglages_evaluation_frappe.surcharges, journal_frappe.journaliser,
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
