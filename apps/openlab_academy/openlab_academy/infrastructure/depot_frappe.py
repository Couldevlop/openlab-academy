"""Adaptateur de sortie : implémente le port DepotCatalogue sur les doctypes Frappe LMS."""
import contextlib
import html

import frappe

from openlab_academy.domain.parcours import Chapitre, Module, Parcours, Question
from openlab_academy.domain.reglages import Reglages
from openlab_academy.infrastructure import editorjs

class DepotFrappe:
    def __init__(self, commit: bool = True, reglages: Reglages | None = None):
        self._commit = commit
        self._reglages = reglages or Reglages()

    # --- port DepotCatalogue -------------------------------------------------
    def trouver(self, titre: str) -> str | None:
        return frappe.db.get_value("LMS Course", {"title": titre})

    def a_des_inscrits(self, cours_id: str) -> bool:
        return bool(frappe.db.count("LMS Enrollment", {"course": cours_id}))

    def creer(self, parcours: Parcours) -> str:
        cours = frappe.get_doc({"doctype": "LMS Course", "instructors": [{"instructor": self._reglages.formateur}],
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
        for quiz in frappe.get_all("LMS Quiz", {"course": cours_id}, pluck="name"):
            questions = frappe.get_all("LMS Quiz Question", {"parent": quiz}, pluck="question")
            frappe.db.delete("LMS Quiz Question", {"parent": quiz})
            frappe.db.delete("LMS Quiz", {"name": quiz})
            if questions:
                frappe.db.delete("LMS Question", {"name": ["in", questions]})
        for chapitre in frappe.get_all("Course Chapter", {"course": cours_id}, pluck="name"):
            frappe.db.delete("Course Lesson", {"chapter": chapitre})
            frappe.db.delete("Course Chapter", {"name": chapitre})
        frappe.db.delete("LMS Assignment", {"course": cours_id})

    def _ecrire_chapitres(self, cours_id: str, parcours: Parcours) -> None:
        noms = [self._chapitre(cours_id, c, parcours.heures_par_module) for c in parcours.chapitres()]
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.set("chapters", [{"chapter": n} for n in noms])
        cours.save(ignore_permissions=True)

    def _chapitre(self, cours_id: str, chapitre: Chapitre, heures_module: int) -> str:
        doc = frappe.get_doc({"doctype": "Course Chapter", "course": cours_id, "title": chapitre.titre}).insert(
            ignore_permissions=True)
        if chapitre.projet is None:
            noms = [self._lecon_module(cours_id, doc.name, m, heures_module) for m in chapitre.modules]
        else:
            noms = [self._lecon_projet(cours_id, doc.name, chapitre)]
        doc.reload()
        doc.set("lessons", [{"lesson": n} for n in noms])
        doc.save(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _devoir(cours_id: str, titre: str, consigne: str, type_: str = "URL") -> str:
        return frappe.get_doc({
            "doctype": "LMS Assignment", "title": titre, "question": consigne,
            "type": type_, "course": cours_id, "grade_assignment": 1,
        }).insert(ignore_permissions=True).name

    @staticmethod
    def _nouvelle_lecon(cours_id: str, chapitre: str, titre: str, contenu: str, evaluations: list[dict]):
        return frappe.get_doc({
            "doctype": "Course Lesson", "course": cours_id, "chapter": chapitre,
            "title": titre, "content": contenu, "assessments": evaluations,
        }).insert(ignore_permissions=True)

    def _lecon_projet(self, cours_id: str, chapitre: str, ch: Chapitre) -> str:
        devoir = self._devoir(cours_id, ch.titre, editorjs.consigne_projet(ch.projet))
        return self._nouvelle_lecon(cours_id, chapitre, f"Énoncé — {ch.projet.titre}",
                                    editorjs.lecon_projet(ch.projet, devoir, self._reglages),
                                    [{"assessment_type": "LMS Assignment", "assessment_name": devoir}]).name

    def _lecon_module(self, cours_id: str, chapitre: str, m: Module, heures: int) -> str:
        devoir = self._devoir(cours_id, f"Livrable {m.num} — {m.title}", editorjs.consigne_module(m))
        evaluations = [{"assessment_type": "LMS Assignment", "assessment_name": devoir}]
        lecon = self._nouvelle_lecon(cours_id, chapitre, f"{m.num} · {m.title}",
                                     editorjs.lecon_module(m, devoir, heures), evaluations)
        if m.quiz:
            quiz = self._quiz(cours_id, lecon.name, m)
            cas = self._devoir(cours_id, f"Mise en situation {m.num} — {m.title}", editorjs.consigne_cas(m), "Text")
            lecon.content = editorjs.lecon_module(m, devoir, heures, quiz, cas, self._reglages)
            lecon.set("assessments", evaluations + [{"assessment_type": "LMS Quiz", "assessment_name": quiz},
                                                    {"assessment_type": "LMS Assignment", "assessment_name": cas}])
            lecon.save(ignore_permissions=True)
        return lecon.name

    def _quiz(self, cours_id: str, lecon: str, m: Module) -> str:
        questions = [self._question(q) for q in m.quiz]
        return frappe.get_doc({
            "doctype": "LMS Quiz", "title": f"Quiz {m.num} — {m.title}", "course": cours_id, "lesson": lecon,
            "max_attempts": self._reglages.tentatives_max, "passing_percentage": self._reglages.score_min,
            "show_answers": 1, "show_submission_history": 1,
            "questions": [{"question": q, "marks": 1} for q in questions],
        }).insert(ignore_permissions=True).name

    @staticmethod
    def _question(q: Question) -> str:
        champs = {"doctype": "LMS Question", "type": "Choices", "question": html.escape(q.enonce),
                  "multiple": int(q.choix_multiple), "marks": 1}
        for i, option in enumerate(q.options, start=1):
            bonne = i in q.bonnes
            champs.update({f"option_{i}": html.escape(option), f"is_correct_{i}": int(bonne),
                           f"explanation_{i}": html.escape(q.explication) if bonne else ""})
        return frappe.get_doc(champs).insert(ignore_permissions=True).name
