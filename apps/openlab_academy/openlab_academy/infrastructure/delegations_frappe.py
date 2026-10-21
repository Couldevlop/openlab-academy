"""Adaptateur : ce que Frappe sait des personnes d'une délégation, sur son périmètre (cours, cohorte, exercice).

Habilitation de correcteur : superviseur (super administrateur, responsable pédagogique), rôle LMS de correction
(formateur ou évaluateur de la plateforme), ou formateur et juré du périmètre lui-même.
"""
import frappe
from frappe.utils import now_datetime

from openlab_academy.domain.delegation import Delegation, FaitsDelegation
from openlab_academy.infrastructure.depot_copies_frappe import INSTRUCTEUR
from openlab_academy.infrastructure.reglages_evaluation_frappe import DELEGATION, ROLE

SUPERVISEURS = {"System Manager", ROLE}
CORRECTEURS_LMS = {"Moderator", "Course Creator", "Batch Evaluator"}


def superviseur(utilisateur: str) -> bool:
    return bool(SUPERVISEURS & set(frappe.get_roles(utilisateur)))


def _cours(d: Delegation) -> str | None:
    if d.cours:
        return d.cours
    return frappe.db.get_value("LMS Assignment", d.exercice, "course") if d.exercice else None


def _cohortes_du_cours(cours: str) -> list[str]:
    return frappe.get_all("Batch Course", {"course": cours, "parenttype": "LMS Batch"}, pluck="parent",
                          parent_doctype="LMS Batch")


def _cohortes(d: Delegation) -> list[str] | None:
    """Cohortes du périmètre ; None : tout le périmètre du titulaire (aucune restriction)."""
    if d.cohorte:
        return [d.cohorte]
    cours = _cours(d)
    return _cohortes_du_cours(cours) if cours else None


def en_propre(utilisateur: str, d: Delegation) -> bool:
    """Formateur ou juré du périmètre par lui-même (instructeur du cours ou de la cohorte, évaluateur du lot)."""
    if superviseur(utilisateur):
        return True
    cours, cohortes = _cours(d), _cohortes(d)
    filtre_lots = {"parent": ["in", cohortes]} if cohortes is not None else {}
    if frappe.get_all(INSTRUCTEUR, {"instructor": utilisateur, "parenttype": "LMS Batch", **filtre_lots},
                      pluck="parent", parent_doctype="LMS Batch", limit=1):
        return True
    filtre_cours = {"parent": cours} if cours else {}
    if not d.cohorte and frappe.get_all(INSTRUCTEUR, {"instructor": utilisateur, "parenttype": "LMS Course",
                                                      **filtre_cours},
                                        pluck="parent", parent_doctype="LMS Course", limit=1):
        return True
    evaluateurs = frappe.get_all("Course Evaluator", {"evaluator": utilisateur}, pluck="name")
    return bool(evaluateurs) and bool(frappe.get_all(
        "Batch Course", {"evaluator": ["in", evaluateurs], "parenttype": "LMS Batch", **filtre_lots},
        pluck="parent", parent_doctype="LMS Batch", limit=1))


def habilite(utilisateur: str, d: Delegation) -> bool:
    return en_propre(utilisateur, d) or bool(CORRECTEURS_LMS & set(frappe.get_roles(utilisateur)))


def apprenant(utilisateur: str, d: Delegation) -> bool:
    """Inscrit comme apprenant dans une cohorte ou un cours du périmètre (tout le périmètre : ceux du titulaire)."""
    cours, cohortes = _cours(d), _cohortes(d)
    if cohortes is None and cours is None:  # périmètre entier : cohortes et cours où le titulaire enseigne
        cohortes = frappe.get_all(INSTRUCTEUR, {"instructor": d.titulaire, "parenttype": "LMS Batch"},
                                  pluck="parent", parent_doctype="LMS Batch")
        cours_titulaire = frappe.get_all(INSTRUCTEUR, {"instructor": d.titulaire, "parenttype": "LMS Course"},
                                         pluck="parent", parent_doctype="LMS Course")
    else:
        cours_titulaire = [cours] if cours else []
    if cohortes and frappe.db.exists("LMS Batch Enrollment", {"member": utilisateur, "batch": ["in", cohortes]}):
        return True
    return bool(cours_titulaire) and bool(
        frappe.db.exists("LMS Enrollment", {"member": utilisateur, "course": ["in", cours_titulaire]}))


def delegataire_actif(utilisateur: str, d: Delegation) -> bool:
    """L'utilisateur détient-il, par une délégation active, une partie de ce périmètre ?"""
    maintenant = now_datetime()
    for r in frappe.get_all(DELEGATION, {"delegataire": utilisateur, "revoquee": 0},
                            ["cohorte", "exercice", "cours", "debut", "fin"]):
        actif = r.fin and r.debut <= maintenant <= r.fin
        recoupe = all(a is None or b is None or a == b for a, b in
                      ((r.cohorte or None, d.cohorte), (r.exercice or None, d.exercice), (r.cours or None, d.cours)))
        if actif and recoupe:
            return True
    return False


def faits(d: Delegation) -> FaitsDelegation:
    return FaitsDelegation(delegataire_apprenant=apprenant(d.delegataire, d),
                           delegataire_habilite=habilite(d.delegataire, d),
                           titulaire_habilite=habilite(d.titulaire, d), titulaire_en_propre=en_propre(d.titulaire, d),
                           titulaire_delegataire=delegataire_actif(d.titulaire, d))
