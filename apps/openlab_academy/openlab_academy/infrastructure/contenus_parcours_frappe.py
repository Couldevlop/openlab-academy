"""Adaptateur Frappe des contenus d'un parcours : parcours d'une leçon ou d'une évaluation, et conditions SQL qui
retirent des listes les contenus des parcours donnés (noms toujours échappés)."""
import frappe


def cours_de_la_lecon(lecon) -> str | None:
    return frappe.db.get_value("Course Lesson", lecon, "course") if isinstance(lecon, str) and lecon else None


def cours_de_l_evaluation(doctype: str, nom: str) -> set[str]:
    """Parcours qui portent l'évaluation : son champ `course`, la leçon d'un quiz, les leçons qui la placent."""
    lecons = set(frappe.get_all("LMS Lesson Assessment", {"assessment_type": doctype, "assessment_name": nom},
                                pluck="parent"))
    champs = [c for c in ("course", "lesson") if frappe.get_meta(doctype).has_field(c)]
    valeurs = frappe.db.get_value(doctype, nom, champs, as_dict=True) if champs else None
    cours = {valeurs.get("course")} if valeurs else set()
    if valeurs and valeurs.get("lesson"):
        lecons.add(valeurs.lesson)
    if lecons:
        cours |= set(frappe.get_all("Course Lesson", {"name": ["in", list(lecons)]}, pluck="course"))
    return {c for c in cours if c}


def _liste(cours: tuple[str, ...]) -> str:
    return ", ".join(frappe.db.escape(c) for c in cours)


def condition_lecons(cours: tuple[str, ...]) -> str:
    return f"ifnull(`tabCourse Lesson`.course, '') not in ({_liste(cours)})" if cours else ""


def condition_evaluations(doctype: str, cours: tuple[str, ...], champ_cours: bool, champ_lecon: bool) -> str:
    if not cours:
        return ""
    liste = _liste(cours)
    conditions = [
        f"`tab{doctype}`.name not in (select la.assessment_name from `tabLMS Lesson Assessment` la"
        f" inner join `tabCourse Lesson` cl on cl.name = la.parent"
        f" where la.assessment_type = {frappe.db.escape(doctype)} and cl.course in ({liste}))"]
    if champ_cours:
        conditions.append(f"ifnull(`tab{doctype}`.course, '') not in ({liste})")
    if champ_lecon:
        conditions.append(f"ifnull(`tab{doctype}`.lesson, '') not in"
                          f" (select cl.name from `tabCourse Lesson` cl where cl.course in ({liste}))")
    return " and ".join(conditions)
