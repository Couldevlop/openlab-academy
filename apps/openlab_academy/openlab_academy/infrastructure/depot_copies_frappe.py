"""Adaptateur : copies, propositions, relectures, grilles d'exercice et cohorte de l'apprenant dans Frappe."""
import html
import json
import re

import frappe
from frappe.utils import get_datetime

from openlab_academy.application.pre_corriger import SIGNALEMENT
from openlab_academy.application.soumettre_copie import Contenu, Exercice
from openlab_academy.domain.copie import Copie, CopieVerrouillee, Etat, Proposition, Source, Statut
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine, TypeExercice

COPIE = "Copie OpenLab"
PROPOSITION = "Proposition OpenLab"
RELECTURE = "Relecture Pair OpenLab"
GRILLE_EXERCICE = "Grille Exercice OpenLab"
AUTO_EVALUATION = "Auto Evaluation OpenLab"
INSTRUCTEUR = "Course Instructor"
SOUMISSION = "LMS Assignment Submission"
JOURNAL = "Journal Note OpenLab"
EN_COURS = [s.value for s in (Statut.RENDUE, Statut.CONTROLEE, Statut.PRE_CORRIGEE, Statut.EN_RELECTURE,
                              Statut.A_CORRIGER)]
_BLOC = re.compile(r"</?(?:p|div|li|ul|ol|h[1-6]|pre|blockquote|table|tr|section|article|header|footer)\b[^>]*>",
                   re.IGNORECASE)
_SAUT = re.compile(r"<br\b[^>]*>", re.IGNORECASE)
_BALISE = re.compile(r"<[^>]*>")
_BLANCS = re.compile(r"[^\S\n]+")


def texte_brut(fragment: str) -> str:
    """Texte d'un rendu HTML : un bloc devient un paragraphe, `<br>` un saut de ligne, toute autre balise une
    espace (deux mots séparés par une balise ne se collent jamais), puis les entités sont décodées."""
    texte = _BALISE.sub(" ", _SAUT.sub("\n", _BLOC.sub("\n\n", fragment)))
    lignes = (_BLANCS.sub(" ", ligne).strip() for ligne in html.unescape(texte).split("\n"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lignes)).strip()


EN_CORRECTION = [Statut.A_CORRIGER.value, Statut.PROVISOIRE.value]


def _json(valeur) -> str:
    return json.dumps(valeur, ensure_ascii=False, sort_keys=True)


def enregistrer_grille_exercice(exercice: str, type_: TypeExercice, grille: Grille, chaine: Chaine | None) -> None:
    """Fige la grille d'un exercice à la publication ; une grille déjà utilisée par des copies n'est jamais modifiée."""
    valeurs = {"type_exercice": type_.value, "grille_json": _json(grille.vers_dict()),
               "chaine_yaml_json": _json(chaine.vers_dict()) if chaine else ""}
    existante = frappe.db.get_value(GRILLE_EXERCICE, {"exercice": exercice})
    if existante is None:
        frappe.get_doc({"doctype": GRILLE_EXERCICE, "exercice": exercice, **valeurs}).insert(ignore_permissions=True)
    elif not frappe.db.exists(COPIE, {"exercice": exercice}):
        frappe.db.set_value(GRILLE_EXERCICE, existante, valeurs)


def a_une_grille(exercice: str) -> bool:
    return bool(frappe.db.exists(GRILLE_EXERCICE, {"exercice": exercice}))


def cours_evalue(exercice: str) -> bool:
    """Le cours de ce devoir a-t-il des exercices avec grille OpenLab ?"""
    cours = frappe.db.get_value("LMS Assignment", exercice, "course")
    devoirs = frappe.get_all("LMS Assignment", filters={"course": cours}, pluck="name") if cours else []
    return bool(devoirs) and bool(frappe.db.exists(GRILLE_EXERCICE, {"exercice": ["in", devoirs]}))


def supprimer_grilles_sans_copie(exercices: list[str]) -> None:
    """Retire les grilles des exercices purgés par une republication, sauf celles qui ont des copies."""
    for exercice in exercices:
        if not frappe.db.exists(COPIE, {"exercice": exercice}):
            frappe.db.delete(GRILLE_EXERCICE, {"exercice": exercice})


CHAMPS_COPIE = ["name", "apprenant", "exercice", "cohorte", "type_exercice", "version", "statut"]
CHAMPS_ETAT = ["etape_courante", "echeance", "escalade_a", "butoir"]


def _etat(ligne) -> Etat:
    return Etat(ligne.etape_courante or "", get_datetime(ligne.echeance) if ligne.echeance else None,
                ligne.escalade_a or "", get_datetime(ligne.butoir) if ligne.butoir else None)


def _copie(doc) -> Copie:
    return Copie(doc.name, doc.apprenant, doc.exercice, doc.cohorte or "", TypeExercice(doc.type_exercice),
                 int(doc.version), Statut(doc.statut))


class DepotCopiesFrappe:
    # --- lecture de l'exercice et du contexte de l'apprenant -----------------
    def exercice(self, exercice: str) -> Exercice | None:
        ligne = frappe.db.get_value(GRILLE_EXERCICE, {"exercice": exercice},
                                    ["type_exercice", "grille_json", "chaine_yaml_json"], as_dict=True)
        if ligne is None:
            return None
        chaine = Chaine.depuis_dict(json.loads(ligne.chaine_yaml_json)) if ligne.chaine_yaml_json else None
        return Exercice(TypeExercice(ligne.type_exercice), Grille.depuis_dict(json.loads(ligne.grille_json)), chaine)

    def cohorte(self, apprenant: str, exercice: str) -> str | None:
        """Le lot (LMS Batch) où l'apprenant est inscrit et qui contient le cours de l'exercice."""
        cours = frappe.db.get_value("LMS Assignment", exercice, "course")
        lots = frappe.get_all("LMS Batch Enrollment", {"member": apprenant}, pluck="batch")
        if not (cours and lots):
            return None
        trouves = frappe.get_all("Batch Course", {"parent": ["in", lots], "course": cours}, pluck="parent",
                                 parent_doctype="LMS Batch", order_by="creation", limit=1)
        return trouves[0] if trouves else None

    def auto_evaluation(self, apprenant: str, exercice: str) -> dict[str, int] | None:
        niveaux = frappe.db.get_value(AUTO_EVALUATION, {"apprenant": apprenant, "exercice": exercice}, "niveaux_json")
        return {c: int(n) for c, n in json.loads(niveaux).items()} if niveaux else None

    def enregistrer_auto_evaluation(self, apprenant: str, exercice: str, niveaux: dict[str, int]) -> None:
        """Une seule auto-évaluation par (apprenant, exercice) : la nouvelle remplace l'ancienne."""
        nom = frappe.db.get_value(AUTO_EVALUATION, {"apprenant": apprenant, "exercice": exercice})
        if nom:
            frappe.db.set_value(AUTO_EVALUATION, nom, "niveaux_json", _json(niveaux))
        else:
            frappe.get_doc({"doctype": AUTO_EVALUATION, "apprenant": apprenant, "exercice": exercice,
                            "niveaux_json": _json(niveaux)}).insert(ignore_permissions=True)

    # --- copies --------------------------------------------------------------
    def signature(self, copie_id: str) -> str:
        return frappe.db.get_value(COPIE, copie_id, "signature") or ""

    def copie(self, copie_id: str) -> Copie:
        return _copie(frappe.get_doc(COPIE, copie_id))

    def creer(self, copie: Copie, grille: Grille, contenu: Contenu) -> str:
        return frappe.get_doc({
            "doctype": COPIE, "soumission": contenu.soumission, "apprenant": copie.apprenant,
            "exercice": copie.exercice, "cohorte": copie.cohorte, "type_exercice": copie.type_.value,
            "version": copie.version, "statut": copie.statut.value, "grille_json": _json(grille.vers_dict()),
            "empreinte": grille.empreinte(), "signature": contenu.signature, "contenu": contenu.texte,
            "source_url": contenu.source_url, "commit": contenu.commit,
        }).insert(ignore_permissions=True).name

    def contenu(self, copie_id: str) -> Contenu:
        ligne = frappe.db.get_value(COPIE, copie_id, ["contenu", "source_url", "commit", "signature", "soumission"],
                                    as_dict=True)
        return Contenu(ligne.contenu or "", ligne.source_url or "", ligne.commit or "", ligne.signature or "",
                       ligne.soumission or "")

    def completer_contenu(self, copie_id: str, texte: str, commit: str) -> None:
        frappe.db.set_value(COPIE, copie_id, {"contenu": texte, "commit": commit})

    def consigne(self, exercice: str) -> str:
        """Consigne du devoir LMS en texte brut (le HTML de la consigne n'est jamais transmis tel quel)."""
        question = frappe.db.get_value("LMS Assignment", exercice, "question") or ""
        return texte_brut(question)

    def titre(self, exercice: str) -> str:
        """Titre du devoir LMS, à défaut son identifiant (texte brut, échappé à l'affichage)."""
        return frappe.db.get_value("LMS Assignment", exercice, "title") or exercice

    def version_courante(self, soumission: str, verrouillee: bool = False) -> Copie | None:
        """Verrouillée : lecture à jour, qui voit une version validée par un rendu concurrent."""
        noms = frappe.db.get_values(COPIE, {"soumission": soumission}, "name", order_by="version desc", limit=1,
                                    for_update=verrouillee, pluck=True)
        return self.copie(noms[0]) if noms else None

    def changer_statut(self, copie_id: str, statut: Statut, etape: str, echeance) -> None:
        frappe.db.set_value(COPIE, copie_id, {"statut": statut.value, "etape_courante": etape, "echeance": echeance})

    # --- propositions et relectures ------------------------------------------
    def ajouter_proposition(self, copie_id: str, p: Proposition) -> None:
        frappe.get_doc({
            "doctype": PROPOSITION, "copie": copie_id, "source": p.source.value, "auteur": p.auteur,
            "au_nom_de": p.au_nom_de or "", "niveaux_json": _json(p.niveaux),
            "commentaires_json": _json(p.commentaires), "citations_json": _json(p.citations),
            "confiance": p.confiance,
        }).insert(ignore_permissions=True)

    def propositions(self, copie_id: str, verrouillee: bool = False) -> list[Proposition]:
        """Verrouillée (après le verrou de la copie) : voit la correction ou le vote validés entre-temps."""
        champs = ["source", "auteur", "niveaux_json", "commentaires_json", "citations_json", "confiance", "au_nom_de"]
        return [Proposition(Source(d.source), d.auteur, json.loads(d.niveaux_json or "{}"),
                            json.loads(d.commentaires_json or "{}"), json.loads(d.citations_json or "{}"),
                            d.confiance, d.au_nom_de or None)
                for d in frappe.db.get_values(PROPOSITION, {"copie": copie_id}, champs, as_dict=True,
                                              order_by="creation", for_update=verrouillee)]

    def annuler_relectures(self, copie_id: str) -> None:
        """Écriture conditionnelle : seules les relectures encore à faire au moment de l'écriture sont annulées,
        jamais une relecture rendue entre-temps par une autre transaction."""
        frappe.db.sql(f"update `tab{RELECTURE}` set statut='annulée', modified=%s where copie=%s and statut='à_faire'",
                      (frappe.utils.now_datetime(), copie_id))

    # --- état dans la chaîne de correction ------------------------------------
    def verrouiller(self, copie_id: str) -> CopieVerrouillee:
        """Verrou de ligne jusqu'à la fin de la transaction, et lecture verrouillante : elle rend la dernière
        version validée de la ligne, pas l'instantané REPEATABLE READ de la transaction."""
        ligne = frappe.db.get_value(COPIE, copie_id, CHAMPS_COPIE + CHAMPS_ETAT, as_dict=True, for_update=True)
        return CopieVerrouillee(_copie(ligne), _etat(ligne))

    def etat(self, copie_id: str) -> Etat:
        return _etat(frappe.db.get_value(COPIE, copie_id, CHAMPS_ETAT, as_dict=True))

    def grille(self, copie_id: str) -> Grille:
        return Grille.depuis_dict(json.loads(frappe.db.get_value(COPIE, copie_id, "grille_json")))

    def copies_echues(self, maintenant) -> list[str]:
        filtres = [["statut", "in", EN_COURS], ["echeance", "is", "set"], ["echeance", "<=", maintenant]]
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="echeance")

    def escalader(self, copie_id: str, destinataire: str, echeance) -> None:
        frappe.db.set_value(COPIE, copie_id, {"escalade_a": destinataire, "echeance": echeance})

    def fixer_butoir(self, copie_id: str, butoir) -> None:
        frappe.db.set_value(COPIE, copie_id, "butoir", butoir)

    def titulaires(self, copie_id: str) -> set[str]:
        """Formateurs de la cohorte, sinon du cours, sinon le formateur des réglages OpenLab Academy."""
        cohorte, exercice = frappe.db.get_value(COPIE, copie_id, ["cohorte", "exercice"])
        noms = frappe.get_all(INSTRUCTEUR, {"parent": cohorte or "", "parenttype": "LMS Batch"},
                              pluck="instructor", parent_doctype="LMS Batch")
        if not noms:
            cours = frappe.db.get_value("LMS Assignment", exercice, "course") or ""
            noms = frappe.get_all(INSTRUCTEUR, {"parent": cours, "parenttype": "LMS Course"},
                                  pluck="instructor", parent_doctype="LMS Course")
        if not noms:
            noms = [frappe.db.get_single_value("Reglages OpenLab Academy", "formateur")]
        return {n for n in noms if n}

    def jures(self, copie_id: str) -> set[str]:
        """Évaluateurs de la cohorte : ceux des cours du lot (LMS Batch), qui forment le jury."""
        cohorte = frappe.db.get_value(COPIE, copie_id, "cohorte")
        evaluateurs = [e for e in frappe.get_all("Batch Course", {"parent": cohorte or "", "parenttype": "LMS Batch"},
                                                 pluck="evaluator", parent_doctype="LMS Batch") if e]
        if not evaluateurs:
            return set()
        return set(frappe.get_all("Course Evaluator", {"name": ["in", evaluateurs]}, pluck="evaluator"))

    # --- correction, publication et retours -------------------------------------
    def copies_en_correction(self, exercice: str | None = None, pour: frozenset[str] | None = None) -> list[str]:
        """Copies à corriger ou provisoires encore dans la chaîne (une version remplacée n'a plus d'étape).

        `pour` (personnes au nom desquelles l'appelant peut agir) préfiltre en base, avant tout contrôle par copie :
        cohortes dont elles sont formatrices ou évaluatrices, devoirs de leurs cours, escalades qui leur sont
        adressées ; le formateur par défaut des réglages garde tout (il est titulaire en dernier recours)."""
        filtres = [["statut", "in", EN_CORRECTION], ["etape_courante", "is", "set"]]
        if exercice:
            filtres.append(["exercice", "=", exercice])
        if pour is not None and frappe.db.get_single_value("Reglages OpenLab Academy", "formateur") not in pour:
            ou = self._perimetre(sorted(pour))
            return frappe.get_all(COPIE, filtres, or_filters=ou, pluck="name", order_by="creation")
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="creation")

    @staticmethod
    def _perimetre(personnes: list[str]) -> list[list]:
        def parents(table, parent, filtres):
            return frappe.get_all(table, {**filtres, "parenttype": parent}, pluck="parent", parent_doctype=parent)
        lots = parents(INSTRUCTEUR, "LMS Batch", {"instructor": ["in", personnes]})
        cours = parents(INSTRUCTEUR, "LMS Course", {"instructor": ["in", personnes]})
        evaluateurs = frappe.get_all("Course Evaluator", {"evaluator": ["in", personnes]}, pluck="name")
        if evaluateurs:  # jurés : évaluateurs des cours du lot
            lots += parents("Batch Course", "LMS Batch", {"evaluator": ["in", evaluateurs]})
        ou = [["escalade_a", "in", personnes]]
        if lots:
            ou.append(["cohorte", "in", lots])
        if cours:
            ou.append(["exercice", "in", frappe.get_all("LMS Assignment", {"course": ["in", cours]}, pluck="name")])
        return ou

    def copies_publiees(self, exercice: str | None = None) -> list[str]:
        filtres = {"statut": Statut.PUBLIEE.value, **({"exercice": exercice} if exercice else {})}
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="creation")

    def publier(self, copie_id: str, note: float, note_sur: int, reussite: bool, resume: str, lien: str,
                differe: bool) -> None:
        """Note figée sur la copie ; dans la soumission LMS, statut et résumé, ou le seul lien si c'est différé."""
        frappe.db.set_value(COPIE, copie_id, {"note": note, "note_sur": note_sur, "reussite": int(reussite),
                                              "lms_differe": int(differe)})
        self._ecrire_lms(copie_id, None if differe else reussite, resume, lien)

    def liberer(self, copie_id: str, reussite: bool, resume: str, lien: str) -> None:
        frappe.db.set_value(COPIE, copie_id, "lms_differe", 0)
        self._ecrire_lms(copie_id, reussite, resume, lien)

    def _ecrire_lms(self, copie_id: str, reussite: bool | None, resume: str, lien: str) -> None:
        """Écriture directe : la validation LMS ramènerait le statut à sa valeur précédente pour un correcteur
        sans rôle LMS privilégié (délégataire), et relancerait le rendu. Le commentaire est construit ici, échappé ;
        `reussite` None laisse le statut LMS inchangé."""
        soumission = frappe.db.get_value(COPIE, copie_id, "soumission")
        if not frappe.db.exists(SOUMISSION, soumission):
            return
        texte = f"{html.escape(resume)} " if resume else ""
        valeurs = {"comments": f'<p>{texte}<a href="{html.escape(lien, quote=True)}">Voir le retour détaillé</a></p>'}
        if reussite is not None:
            valeurs["status"] = "Pass" if reussite else "Fail"
        frappe.db.set_value(SOUMISSION, soumission, valeurs)

    def differee(self, copie_id: str) -> bool:
        """Lecture verrouillante : la dernière valeur validée, jamais l'instantané de la transaction."""
        return bool(frappe.db.get_value(COPIE, copie_id, "lms_differe", for_update=True))

    def copies_differees(self, apprenant: str | None = None) -> list[str]:
        filtres = {"lms_differe": 1, "statut": Statut.PUBLIEE.value, **({"apprenant": apprenant} if apprenant else {})}
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="creation")

    def resultat(self, copie_id: str) -> tuple[float, int, bool]:
        """Note figée à la publication (lue pour une copie publiée seulement)."""
        ligne = frappe.db.get_value(COPIE, copie_id, ["note", "note_sur", "reussite"], as_dict=True)
        return float(ligne.note or 0), int(ligne.note_sur or 0), bool(ligne.reussite)

    def dispensee(self, copie_id: str) -> bool:
        return bool(frappe.db.get_value(COPIE, copie_id, "relectures_dispensees"))

    def signalee(self, copie_id: str) -> bool:
        return bool(frappe.db.exists(JOURNAL, {"copie": copie_id, "action": SIGNALEMENT}))

    def texte_lisible(self, copie_id: str) -> str:
        """Texte brut de la copie : un rendu texte LMS (HTML) est réduit à son texte, jamais renvoyé en HTML."""
        contenu = self.contenu(copie_id)
        if contenu.rendu_par_lien:
            return contenu.texte
        return texte_brut(contenu.texte)

    def texte_compact(self, copie_id: str) -> str:
        """Texte de la copie, balises retirées sans rien à leur place (un mot coupé par une balise est recollé) :
        sert seulement à la détection des tournures d'injection."""
        return html.unescape(_BALISE.sub("", self.contenu(copie_id).texte))

    def existe(self, copie_id: str) -> bool:
        return bool(copie_id) and bool(frappe.db.exists(COPIE, copie_id))

    # --- auto-évaluation -----------------------------------------------------
    def inscrit(self, apprenant: str, exercice: str) -> bool:
        cours = frappe.db.get_value("LMS Assignment", exercice, "course")
        return bool(cours) and bool(frappe.db.exists("LMS Enrollment", {"member": apprenant, "course": cours}))

    def derniere_copie(self, apprenant: str, exercice: str) -> Copie | None:
        noms = frappe.get_all(COPIE, {"apprenant": apprenant, "exercice": exercice}, pluck="name",
                              order_by="version desc", limit=1)
        return self.copie(noms[0]) if noms else None
