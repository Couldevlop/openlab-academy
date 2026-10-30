"""Inscription à un parcours limité à ses dates : rattachée à sa cohorte-fenêtre, pour que l'apprenant la retrouve
comme les autres."""
import frappe

from openlab_academy.entrypoints.lms import _exempte
from openlab_academy.infrastructure.depot_cohortes_frappe import DepotCohortesFrappe
from openlab_academy.infrastructure.visibilite_frappe import SourceVisibiliteFrappe

INSCRIPTION_COHORTE = "LMS Batch Enrollment"


def rejoindre_cohorte(doc, method=None) -> None:
    """`after_insert` de LMS Enrollment : parcours limité, membre non agent, inscription qui ne vient pas déjà d'une
    cohorte -> inscription à la cohorte-fenêtre, si elle n'existe pas. Sans effet sinon (rejouable, sans boucle :
    l'inscription que la cohorte crée porte `enrollment_from_batch` ou le drapeau du LMS)."""
    if doc.enrollment_from_batch or doc.flags.via_batch_enrollment or _exempte(doc.member):
        return
    if not SourceVisibiliteFrappe().limite(doc.course):
        return
    lot = DepotCohortesFrappe().fenetre_de(doc.course)
    if lot is None or frappe.db.exists(INSCRIPTION_COHORTE, {"batch": lot, "member": doc.member}):
        return
    frappe.get_doc({"doctype": INSCRIPTION_COHORTE, "batch": lot, "member": doc.member}).insert(
        ignore_permissions=True)
