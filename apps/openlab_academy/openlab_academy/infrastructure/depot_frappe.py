"""Adaptateur de sortie : implémente le port DepotCatalogue sur les doctypes Frappe LMS."""
import contextlib

import frappe

from openlab_academy.domain.parcours import Chapitre, Parcours
from openlab_academy.infrastructure import editorjs

INSTRUCTEUR = "Administrator"


class DepotFrappe:
    def __init__(self, commit: bool = True):
        self._commit = commit

    # --- port DepotCatalogue -------------------------------------------------
    def trouver(self, titre: str) -> str | None:
        return frappe.db.get_value("LMS Course", {"title": titre})

    def a_des_inscrits(self, cours_id: str) -> bool:
        return bool(frappe.db.count("LMS Enrollment", {"course": cours_id}))

    def creer(self, parcours: Parcours) -> str:
        cours = frappe.get_doc({"doctype": "LMS Course", "instructors": [{"instructor": INSTRUCTEUR}],
                                **self._champs(parcours)}).insert(ignore_permissions=True)
        self._ecrire_chapitres(cours.name, parcours)
        return cours.name

    def remplacer(self, cours_id: str, parcours: Parcours) -> None:
        self._purger(cours_id)
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.update(self._champs(parcours))
        cours.set("chapters", [])
        cours.save(ignore_permissions=True)
        self._ecrire_chapitres(cours_id, parcours)

    @contextlib.contextmanager
    def unite_de_travail(self):
        frappe.db.savepoint("openlab_publication")
        try:
            yield
        except Exception:
            frappe.db.rollback(save_point="openlab_publication")
            raise
        if self._commit:
            frappe.db.commit()

    # --- détails -------------------------------------------------------------
    @staticmethod
    def _champs(p: Parcours) -> dict:
        return {"title": p.title, "short_introduction": p.short_introduction, "description": p.description,
                "tags": ",".join(p.tags), "card_gradient": p.card_gradient,
                "published": 1, "enable_certification": 1}

    @staticmethod
    def _purger(cours_id: str) -> None:
        for chapitre in frappe.get_all("Course Chapter", {"course": cours_id}, pluck="name"):
            frappe.db.delete("Course Lesson", {"chapter": chapitre})
            frappe.db.delete("Course Chapter", {"name": chapitre})
        frappe.db.delete("LMS Assignment", {"course": cours_id})

    def _ecrire_chapitres(self, cours_id: str, parcours: Parcours) -> None:
        noms = [self._chapitre(cours_id, c) for c in parcours.chapitres()]
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.set("chapters", [{"chapter": n} for n in noms])
        cours.save(ignore_permissions=True)

    def _chapitre(self, cours_id: str, chapitre: Chapitre) -> str:
        doc = frappe.get_doc({"doctype": "Course Chapter", "course": cours_id, "title": chapitre.titre}).insert(
            ignore_permissions=True)
        if chapitre.projet is None:
            lecons = [(f"{m.num} · {m.title}", f"Livrable {m.num} — {m.title}",
                       editorjs.consigne_module(m), lambda d, m=m: editorjs.lecon_module(m, d))
                      for m in chapitre.modules]
        else:
            p = chapitre.projet
            lecons = [(f"Énoncé — {p.titre}", chapitre.titre, editorjs.consigne_projet(p),
                       lambda d: editorjs.lecon_projet(p, d))]
        noms = [self._lecon(cours_id, doc.name, *lecon) for lecon in lecons]
        doc.reload()
        doc.set("lessons", [{"lesson": n} for n in noms])
        doc.save(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _lecon(cours_id: str, chapitre: str, titre: str, titre_devoir: str, consigne: str, rendu) -> str:
        devoir = frappe.get_doc({
            "doctype": "LMS Assignment", "title": titre_devoir, "question": consigne,
            "type": "URL", "course": cours_id, "grade_assignment": 1,
        }).insert(ignore_permissions=True).name
        return frappe.get_doc({
            "doctype": "Course Lesson", "course": cours_id, "chapter": chapitre,
            "title": titre, "content": rendu(devoir),
            "assessments": [{"assessment_type": "LMS Assignment", "assessment_name": devoir}],
        }).insert(ignore_permissions=True).name
