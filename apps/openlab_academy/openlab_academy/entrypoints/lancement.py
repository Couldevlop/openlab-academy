"""Parcours limité à ses dates : inscription rattachée à sa cohorte-fenêtre, pour que l'apprenant la retrouve comme
les autres, et retrait quotidien du catalogue une fois la fenêtre terminée."""
import frappe

from openlab_academy.application.visibilite import Visibilite
from openlab_academy.entrypoints import lms
from openlab_academy.entrypoints.lms import _exempte, issue_de_cohorte
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.visibilite_frappe import SourceVisibiliteFrappe

INSCRIPTION_COHORTE = "LMS Batch Enrollment"


def rejoindre_cohorte(doc, method=None) -> None:
    """`after_insert` de LMS Enrollment : parcours limité, membre non agent, inscription qui ne vient pas déjà d'une
    cohorte -> inscription à la cohorte-fenêtre, si elle n'existe pas. Sans effet sinon (rejouable, sans boucle :
    l'inscription que la cohorte crée porte `enrollment_from_batch` ou le drapeau du LMS)."""
    if doc.enrollment_from_batch or issue_de_cohorte(doc) or _exempte(doc.member):
        return
    if not SourceVisibiliteFrappe().limite(doc.course):
        return
    lot = DepotCohortesFrappe().fenetre_de(doc.course)
    if lot is None or frappe.db.exists(INSCRIPTION_COHORTE, {"batch": lot, "member": doc.member}):
        return
    frappe.get_doc({"doctype": INSCRIPTION_COHORTE, "batch": lot, "member": doc.member}).insert(
        ignore_permissions=True)


def retirer_parcours_echus(commit: bool = True) -> tuple[str, ...]:
    """Tâche quotidienne (00:05, heure du site) : les parcours limités dont la fenêtre est terminée quittent le
    catalogue (`published = 0`). Rien d'autre n'est touché ; rejouable (un parcours déjà retiré n'est plus
    publié). Appelée aussi en dernier par `after_migrate`, qui republie les parcours juste avant."""
    source = SourceVisibiliteFrappe()
    echus = Visibilite(source, lambda: lms.aujourd_hui()).echus()
    for cours in echus:
        source.depublier(cours)
        frappe.logger("openlab_academy").info("Parcours retiré du catalogue après sa fermeture : %s", cours)
    if echus and commit:
        frappe.db.commit()
    return echus
