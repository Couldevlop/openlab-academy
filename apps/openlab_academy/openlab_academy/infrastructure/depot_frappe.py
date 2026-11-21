"""Adaptateur de sortie : implémente le port DepotCatalogue sur les doctypes Frappe LMS."""
import contextlib
import dataclasses
import html
from urllib.parse import quote

import frappe

from openlab_academy.domain.grille import Grille
from openlab_academy.domain.grilles_derivees import grille_par_defaut
from openlab_academy.domain.parcours import (Annonce, BlocAnnonce, Chapitre, Module, Parcours,
                                             Question)
from openlab_academy.domain.reglages import Reglages, ReglagesExercices
from openlab_academy.domain.reglages_evaluation import Chaine, ReglagesEvaluation, TypeExercice
from openlab_academy.infrastructure import domaines_frappe
from openlab_academy.infrastructure import (depot_copies_frappe, editorjs, parties_frappe, ressources_frappe,
                                            retouches_frappe)
from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT
from openlab_academy.infrastructure.depot_ouvertures_frappe import CHAMP_DELAI
from openlab_academy.infrastructure.visibilite_frappe import CHAMP_LIMITE, CHAMP_VIDEO

# champ du LMS : une leçon ne s'ouvre qu'une fois la précédente terminée
CHAMP_SEQUENTIEL = "enforce_lesson_completion"


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
        with retouches_frappe.publication():
            return self._creer(parcours)

    def _creer(self, parcours: Parcours | Annonce) -> str:
        cours = frappe.get_doc({"doctype": "LMS Course", "instructors": [{"instructor": self._reglages.formateur}],
                                **self._champs(parcours)}).insert(ignore_permissions=True)
        self._couverture(cours.name, parcours)
        if isinstance(parcours, Parcours):
            self._ecrire_chapitres(cours.name, parcours)
        else:
            self._ecrire_programme_annonce(cours.name, parcours)
        return cours.name

    def remplacer(self, cours_id: str, parcours: Parcours | Annonce) -> None:
        """Ce qui a été retouché dans l'application est conservé : séances, challenges, questions de quiz et
        fiche du parcours. Le fichier réécrit tout le reste, et ne reprend une pièce retouchée que lorsque sa
        case est décochée."""
        with retouches_frappe.publication():
            self._remplacer(cours_id, parcours)

    def _remplacer(self, cours_id: str, parcours: Parcours | Annonce) -> None:
        videos = self._videos(cours_id)
        retouchees = retouches_frappe.relever(cours_id)
        parties_retouchees = parties_frappe.relever(cours_id)
        anciens = retouches_frappe.exercices(cours_id)
        self._purger(cours_id)
        # lecture verrouillante : l'instantané de la transaction date d'avant la purge et ne voit pas le `modified`
        # qu'une tâche planifiée du LMS (statistiques horaires) a validé entre-temps ; le verrou la fait attendre
        cours = frappe.get_doc("LMS Course", cours_id, for_update=True)
        cours.update(retouches_frappe.champs_du_parcours(cours_id, self._champs(parcours)))
        cours.set("chapters", [])
        cours.save(ignore_permissions=True)
        self._couverture(cours_id, parcours)
        if isinstance(parcours, Parcours):
            self._ecrire_chapitres(cours_id, parcours, videos)
            retouches_frappe.reconduire(cours_id, retouchees, anciens)
            parties_frappe.reconduire(cours_id, parties_retouchees,
                                      retouches_frappe.remplacements(cours_id, anciens))
        else:
            # Pas de reconduction des retouches : il n'y a rien a retoucher sur un plan annonce, et
            # le fichier en est la seule source. La purge a deja vide les chapitres.
            self._ecrire_programme_annonce(cours_id, parcours)

    @staticmethod
    def _couverture(cours_id: str, parcours: Parcours | Annonce) -> None:
        """L'image de couverture est jointe après la création : un média ne se joint qu'à un document existant."""
        if not parcours.couverture:
            return
        adresse = ressources_frappe.joindre_couverture(cours_id, parcours.couverture)
        frappe.db.set_value("LMS Course", cours_id, "image", adresse)

    @staticmethod
    def _couverture_si_non_retouchee(cours_id: str, parcours: Parcours | Annonce) -> None:
        """Couverture d'un parcours que la publication laisse par ailleurs tel quel."""
        if retouches_frappe.fiche_retouchee(cours_id):
            return
        DepotFrappe._couverture(cours_id, parcours)

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
        champs = {"title": p.title, "short_introduction": p.short_introduction, "description": p.description,
                  "tags": ",".join(p.tags), "card_gradient": p.card_gradient,
                  "published": 1, "enable_certification": 1, "upcoming": int(isinstance(p, Annonce))}
        # Domaine seulement s'il est demandé : absent du fichier, le choix fait dans l'administration
        # n'est pas effacé — même règle que pour la gratuité et la mise en avant.
        if p.domaine:
            champs[domaines_frappe.CHAMP] = domaines_frappe.exiger(p.domaine)
        if isinstance(p, Parcours):
            champs.update(DepotFrappe._drapeaux(p))
        return champs

    @staticmethod
    def _drapeaux(p: Parcours) -> dict:
        """Accès limité, délai des exercices et progression séquentielle toujours écrits ; gratuit et mise en avant seulement s'ils sont
        demandés : absents, la décision de l'administrateur n'est pas écrasée."""
        drapeaux = {CHAMP_LIMITE: int(p.acces_limite_a_la_cohorte), CHAMP_DELAI: p.exercices.delai_minutes,
                    CHAMP_SEQUENTIEL: int(p.progression_sequentielle)}
        if p.gratuit:
            drapeaux[CHAMP_GRATUIT] = 1
        if p.mise_en_avant:
            drapeaux["featured"] = 1
        return drapeaux

    @staticmethod
    def _videos(cours_id: str) -> dict[str, str]:
        """{titre de leçon: vidéo} des leçons du parcours, relevé avant leur suppression."""
        lecons = frappe.get_all("Course Lesson", {"course": cours_id}, ["title", CHAMP_VIDEO])
        return {l.title: l[CHAMP_VIDEO] for l in lecons if l[CHAMP_VIDEO]}

    @staticmethod
    def _purger(cours_id: str) -> None:
        """Supprime le contenu du parcours document par document : hooks du LMS joués (on_trash des leçons) et
        lignes enfants supprimées avec leur parent. force : ces documents se citent entre eux et partent ensemble."""
        def supprimer(doctype: str, nom: str) -> None:
            frappe.delete_doc(doctype, nom, force=True, ignore_permissions=True, delete_permanently=True)

        depot_copies_frappe.supprimer_grilles_sans_copie(frappe.get_all("LMS Assignment", {"course": cours_id}, pluck="name"))
        for chapitre in frappe.get_all("Course Chapter", {"course": cours_id}, pluck="name"):
            for lecon in frappe.get_all("Course Lesson", {"chapter": chapitre}, pluck="name"):
                supprimer("Course Lesson", lecon)
            supprimer("Course Chapter", chapitre)
        for quiz in frappe.get_all("LMS Quiz", {"course": cours_id}, pluck="name"):
            questions = frappe.get_all("LMS Quiz Question", {"parent": quiz}, pluck="question")
            supprimer("LMS Quiz", quiz)
            for question in questions:
                supprimer("LMS Question", question)
        for devoir in frappe.get_all("LMS Assignment", {"course": cours_id}, pluck="name"):
            supprimer("LMS Assignment", devoir)

    def _ecrire_programme_annonce(self, cours_id: str, annonce: Annonce) -> None:
        """Le plan annoncé devient des chapitres et des séances vides.

        Vides littéralement : ni contenu, ni devoir, ni quiz. Une séance annoncée n'est pas une
        séance au rabais qu'on remplirait plus tard d'un texte d'attente — c'est une ligne du plan,
        et le LMS n'a besoin que de son titre pour l'afficher. Ce qui ouvre un parcours reste
        `upcoming`, que ce chemin ne touche pas : remplir la fiche ne doit jamais ouvrir la porte.
        """
        if not annonce.programme:
            return
        noms = [self._bloc_annonce(cours_id, bloc) for bloc in annonce.programme]
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.set("chapters", [{"chapter": n} for n in noms])
        cours.save(ignore_permissions=True)

    def _bloc_annonce(self, cours_id: str, bloc: BlocAnnonce) -> str:
        doc = frappe.get_doc({"doctype": "Course Chapter", "course": cours_id,
                              "title": bloc.titre}).insert(ignore_permissions=True)
        noms = [self._nouvelle_lecon(cours_id, doc.name, titre, "", []).name for titre in bloc.seances]
        doc.reload()
        doc.set("lessons", [{"lesson": n} for n in noms])
        doc.save(ignore_permissions=True)
        return doc.name

    def _ecrire_chapitres(self, cours_id: str, parcours: Parcours, videos: dict[str, str] | None = None) -> None:
        videos = videos or {}
        noms = [self._chapitre(cours_id, c, parcours, videos) for c in parcours.chapitres()]
        cours = frappe.get_doc("LMS Course", cours_id)
        cours.set("chapters", [{"chapter": n} for n in noms])
        cours.save(ignore_permissions=True)

    def _chapitre(self, cours_id: str, chapitre: Chapitre, parcours: Parcours, videos: dict[str, str]) -> str:
        doc = frappe.get_doc({"doctype": "Course Chapter", "course": cours_id, "title": chapitre.titre}).insert(
            ignore_permissions=True)
        if chapitre.projet is None:
            noms = [self._lecon_module(cours_id, doc.name, m, parcours, videos) for m in chapitre.modules]
        else:
            noms = [self._lecon_projet(cours_id, doc.name, chapitre, videos)]
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
        """Cours conservé tel quel (inscrits) : applique les drapeaux de lancement, rafraîchit la couverture et
        le domaine, et crée seulement les grilles manquantes de ses devoirs, par titre.

        La couverture est une vitrine, pas du contenu : la poser ne change rien pour les inscrits, et sans cela
        un parcours en cours garderait à jamais l'image de sa première publication. La fiche retouchée dans
        l'application reste intouchée, comme pour une republication complète.

        Le domaine suit la même règle, et pour la même raison. C'est la famille du parcours, donc la teinte de
        sa carte : de la présentation, jamais du contenu. Sans cela, les parcours les plus avancés — ceux qui
        ont des inscrits — seraient précisément ceux qui resteraient gris au catalogue."""
        self._couverture_si_non_retouchee(cours_id, parcours)
        self._domaine(cours_id, parcours)
        if isinstance(parcours, Annonce):
            return
        frappe.db.set_value("LMS Course", cours_id, self._drapeaux(parcours))
        for titre, type_exercice, projet, grille, chaine in self._exercices(parcours):
            nom = frappe.db.get_value("LMS Assignment", {"course": cours_id, "title": titre})
            if nom and not depot_copies_frappe.a_une_grille(nom):
                self._figer(nom, type_exercice, projet, grille, chaine)

    @staticmethod
    def _domaine(cours_id: str, parcours: Parcours | Annonce) -> None:
        """La famille du parcours, posée sans toucher au reste. Absente du fichier, le choix fait dans
        l'administration n'est pas effacé."""
        if parcours.domaine:
            frappe.db.set_value("LMS Course", cours_id, domaines_frappe.CHAMP,
                                domaines_frappe.exiger(parcours.domaine))

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
                if m.veut_livrable:
                    yield (f"Livrable {m.num} — {m.title}", TypeExercice.LIVRABLE, None, m.grille_livrable,
                           m.correction_livrable)
                if m.quiz:
                    yield (f"Mise en situation {m.num} — {m.title}", TypeExercice.MISE_EN_SITUATION, None,
                           m.grille_cas, m.correction_cas)

    @staticmethod
    def _nouvelle_lecon(cours_id: str, chapitre: str, titre: str, contenu: str, evaluations: list[dict],
                        video: str = ""):
        return frappe.get_doc({
            "doctype": "Course Lesson", "course": cours_id, "chapter": chapitre,
            "title": titre, "content": contenu, "assessments": evaluations, CHAMP_VIDEO: video,
        }).insert(ignore_permissions=True)

    def _lecon_projet(self, cours_id: str, chapitre: str, ch: Chapitre, videos: dict[str, str]) -> str:
        type_exercice = self._type_projet(ch.projet)
        devoir = self._devoir(cours_id, ch.titre, editorjs.consigne_projet(ch.projet), type_exercice, ch.projet,
                              ch.projet.grille, ch.projet.correction)
        titre = f"Énoncé — {ch.projet.titre}"
        # mêmes deux passes que pour une séance : un média ne se joint qu'à une leçon déjà créée
        sans_media = dataclasses.replace(
            ch.projet, figures=(), cours=tuple(dataclasses.replace(s, figures=()) for s in ch.projet.cours))
        lecon = self._nouvelle_lecon(cours_id, chapitre, titre,
                                     editorjs.lecon_projet(sans_media, devoir, self._reglages),
                                     [{"assessment_type": "LMS Assignment", "assessment_name": devoir}],
                                     videos.get(titre, ""))
        figures = {f.nom: ressources_frappe.joindre(lecon.name, f.nom) for f in ch.projet.toutes_les_figures}
        rubriques = editorjs.rubriques_projet(ch.projet, devoir, self._reglages, figures)
        self._poser_parties(lecon, rubriques)
        return lecon.name

    def _lecon_module(self, cours_id: str, chapitre: str, m: Module, parcours: Parcours,
                      videos: dict[str, str]) -> str:
        heures = parcours.heures_par_module
        # une séance de quiz seul (rappel) ne crée pas de devoir : le LMS attendrait un rendu qui n'existe pas
        devoir = (self._devoir(cours_id, f"Livrable {m.num} — {m.title}", editorjs.consigne_module(m),
                               TypeExercice.LIVRABLE, grille=m.grille_livrable, chaine=m.correction_livrable)
                  if m.veut_livrable else None)
        evaluations = ([{"assessment_type": "LMS Assignment", "assessment_name": devoir}] if devoir else [])
        titre = f"{m.num} · {m.title}"
        # un média ne se joint qu'à une leçon existante : la première passe écrit le contenu sans les médias,
        # la seconde le réécrit une fois les adresses connues
        sans_media = dataclasses.replace(
            m, figures=(), cours=tuple(dataclasses.replace(s, figures=()) for s in m.cours))
        lecon = self._nouvelle_lecon(cours_id, chapitre, titre,
                                     editorjs.lecon_module(sans_media, devoir, heures),
                                     evaluations, videos.get(titre, ""))
        url = ressources_frappe.joindre(lecon.name, m.archive) if m.archive else None
        figures = {f.nom: ressources_frappe.joindre(lecon.name, f.nom) for f in m.toutes_les_figures}
        quiz = self._quiz(cours_id, lecon.name, m, parcours.exercices) if m.veut_quiz and m.quiz else None
        # la mise en situation accompagne le quiz d'une séance complète ; seule, personne ne la corrigerait
        cas = (self._devoir(cours_id, f"Mise en situation {m.num} — {m.title}", editorjs.consigne_cas(m),
                            TypeExercice.MISE_EN_SITUATION, grille=m.grille_cas, chaine=m.correction_cas,
                            type_="Text")
               if quiz and m.mise_en_situation.strip() else None)
        # l'atelier ouvre le dépôt du jour dans le navigateur : il n'existe que pour les séances qui le déclarent
        atelier = f"/atelier?lecon={quote(lecon.name, safe='')}" if m.atelier else None
        rubriques = editorjs.rubriques_module(m, devoir, heures, quiz, cas, parcours.exercices, url, figures,
                                              atelier)
        if quiz:
            evaluations = evaluations + [{"assessment_type": "LMS Quiz", "assessment_name": quiz}]
        if cas:
            evaluations = evaluations + [{"assessment_type": "LMS Assignment", "assessment_name": cas}]
        lecon.set("assessments", evaluations)
        self._poser_parties(lecon, rubriques)
        return lecon.name

    @staticmethod
    def _poser_parties(lecon, rubriques) -> None:
        """Dépose les parties de la leçon, puis écrit son contenu assemblé depuis elles : la leçon que lit
        l'apprenant et les parties qu'édite l'administrateur ne peuvent pas diverger."""
        lecon.content = editorjs.assembler(rubriques)
        lecon.save(ignore_permissions=True)
        parties_frappe.ecrire(lecon.name, rubriques)

    def _quiz(self, cours_id: str, lecon: str, m: Module, exercices: ReglagesExercices) -> str:
        questions = [self._question(q) for q in m.quiz]
        return frappe.get_doc({
            "doctype": "LMS Quiz", "title": f"Quiz {m.num} — {m.title}", "course": cours_id, "lesson": lecon,
            "max_attempts": exercices.tentatives_max, "passing_percentage": exercices.score_min,
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
