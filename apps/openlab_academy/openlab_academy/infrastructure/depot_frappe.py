"""Adaptateur de sortie : implémente le port DepotCatalogue sur les doctypes Frappe LMS."""
import contextlib
import html

import frappe

from openlab_academy.domain.grille import Grille
from openlab_academy.domain.grilles_derivees import grille_par_defaut
from openlab_academy.domain.parcours import Annonce, Chapitre, Module, Parcours, Question
from openlab_academy.domain.reglages import Reglages
from openlab_academy.domain.reglages_evaluation import Chaine, ReglagesEvaluation, TypeExercice
from openlab_academy.infrastructure import depot_copies_frappe, editorjs

class DepotFrappe:
    def __init__(self, commit: bool = True, reglages: Reglages | None = None,
                 evaluation: ReglagesEvaluation | None = None):
        self._commit = commit
        self._reglages = reglages or Reglages()
        self._evaluation = evaluation or ReglagesEvaluation()

    # --- port DepotCatalogue -------------------------------------------------
    def trouver(self, titre: str) -> str | None:
        return frappe.db.get_value("LMS Course", {"title": titre})

    def a_des_inscrits(self, cours_id: str) -> bool:
        return bool(frappe.db.count("LMS Enrollment", {"course": cours_id}))

    def creer(self, parcours: Parcours | Annonce) -> str:
        cours = frappe.get_doc({"doctype": "LMS Course", "instructors": [{"instructor": self._reglages.formateur}],
                                **self._champs(parcours)}).insert(ignore_permissions=True)
        if isinstance(parcours, Parcours):
            self._ecrire_chapitres(cours.name, parcours)
        return cours.name

    def remplacer(self, cours_id: str, parcours: Parcours | Annonce) -> None:
        self._purger(cours_id)
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.update(self._champs(parcours))
        cours.set("chapters", [])
        cours.save(ignore_permissions=True)
        if isinstance(parcours, Parcours):
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
    def _champs(p: Parcours | Annonce) -> dict:
        return {"title": p.title, "short_introduction": p.short_introduction, "description": p.description,
                "tags": ",".join(p.tags), "card_gradient": p.card_gradient,
                "published": 1, "enable_certification": 1, "upcoming": int(isinstance(p, Annonce))}

    @staticmethod
    def _purger(cours_id: str) -> None:
        depot_copies_frappe.supprimer_grilles_sans_copie(frappe.get_all("LMS Assignment", {"course": cours_id}, pluck="name"))
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

    def _devoir(self, cours_id: str, titre: str, consigne: str, type_exercice: TypeExercice, projet=None,
                grille: Grille | None = None, chaine: Chaine | None = None, type_: str = "URL") -> str:
        """Crée le devoir LMS et fige sa grille (celle du YAML, sinon dérivée des réglages) et sa chaîne éventuelle."""
        nom = frappe.get_doc({
            "doctype": "LMS Assignment", "title": titre, "question": consigne,
            "type": type_, "course": cours_id, "grade_assignment": 1,
        }).insert(ignore_permissions=True).name
        self._figer(nom, type_exercice, projet, grille, chaine)
        return nom

    def _figer(self, nom: str, type_exercice: TypeExercice, projet, grille: Grille | None, chaine: Chaine | None):
        grille = grille or grille_par_defaut(type_exercice, projet, self._reglages, self._evaluation)
        depot_copies_frappe.enregistrer_grille_exercice(nom, type_exercice, grille, chaine)

    def completer(self, cours_id: str, parcours: Parcours | Annonce) -> None:
        """Cours conservé tel quel (inscrits) : crée seulement les grilles manquantes de ses devoirs, par titre."""
        if isinstance(parcours, Annonce):
            return
        for titre, type_exercice, projet, grille, chaine in self._exercices(parcours):
            nom = frappe.db.get_value("LMS Assignment", {"course": cours_id, "title": titre})
            if nom and not depot_copies_frappe.a_une_grille(nom):
                self._figer(nom, type_exercice, projet, grille, chaine)

    @staticmethod
    def _type_projet(projet) -> TypeExercice:
        return TypeExercice.CAPSTONE if projet.apres_module is None else TypeExercice.PROJET

    def _exercices(self, parcours: Parcours):
        """(titre du devoir, type, projet, grille, chaîne) de chaque exercice du parcours."""
        for chapitre in parcours.chapitres():
            if chapitre.projet is not None:
                p = chapitre.projet
                yield chapitre.titre, self._type_projet(p), p, p.grille, p.correction
            for m in chapitre.modules:
                yield f"Livrable {m.num} — {m.title}", TypeExercice.LIVRABLE, None, m.grille_livrable, m.correction_livrable
                if m.quiz:
                    yield (f"Mise en situation {m.num} — {m.title}", TypeExercice.MISE_EN_SITUATION, None,
                           m.grille_cas, m.correction_cas)

    @staticmethod
    def _nouvelle_lecon(cours_id: str, chapitre: str, titre: str, contenu: str, evaluations: list[dict]):
        return frappe.get_doc({
            "doctype": "Course Lesson", "course": cours_id, "chapter": chapitre,
            "title": titre, "content": contenu, "assessments": evaluations,
        }).insert(ignore_permissions=True)

    def _lecon_projet(self, cours_id: str, chapitre: str, ch: Chapitre) -> str:
        type_exercice = self._type_projet(ch.projet)
        devoir = self._devoir(cours_id, ch.titre, editorjs.consigne_projet(ch.projet), type_exercice, ch.projet,
                              ch.projet.grille, ch.projet.correction)
        return self._nouvelle_lecon(cours_id, chapitre, f"Énoncé — {ch.projet.titre}",
                                    editorjs.lecon_projet(ch.projet, devoir, self._reglages),
                                    [{"assessment_type": "LMS Assignment", "assessment_name": devoir}]).name

    def _lecon_module(self, cours_id: str, chapitre: str, m: Module, heures: int) -> str:
        devoir = self._devoir(cours_id, f"Livrable {m.num} — {m.title}", editorjs.consigne_module(m),
                              TypeExercice.LIVRABLE, grille=m.grille_livrable, chaine=m.correction_livrable)
        evaluations = [{"assessment_type": "LMS Assignment", "assessment_name": devoir}]
        lecon = self._nouvelle_lecon(cours_id, chapitre, f"{m.num} · {m.title}",
                                     editorjs.lecon_module(m, devoir, heures), evaluations)
        if m.quiz:
            quiz = self._quiz(cours_id, lecon.name, m)
            cas = self._devoir(cours_id, f"Mise en situation {m.num} — {m.title}", editorjs.consigne_cas(m),
                               TypeExercice.MISE_EN_SITUATION, grille=m.grille_cas, chaine=m.correction_cas,
                               type_="Text")
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
