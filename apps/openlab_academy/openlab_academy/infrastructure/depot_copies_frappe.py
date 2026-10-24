"""Adaptateur : copies, propositions, relectures, grilles d'exercice et cohorte de l'apprenant dans Frappe."""
import html
import json
import re

import frappe
from frappe.utils import get_datetime

from openlab_academy.application.pre_corriger import SIGNALEMENT
from openlab_academy.application.soumettre_copie import Contenu, Exercice
from openlab_academy.domain.copie import (
    Copie, CopieVerrouillee, Etat, EtatInstantane, Proposition, Source, Statut)
from openlab_academy.domain.equipe import EquipeEffective, resoudre_equipe
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine, CopieEnCours, TypeExercice
from openlab_academy.infrastructure import reglages_evaluation_frappe

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


def marquer_versions_remplacees() -> None:
    """Reprise des données : une version sortie de la chaîne (sans étape) alors qu'une version plus récente de la
    même soumission existe était l'ancien marquage d'un remplacement ; elle reçoit le statut « remplacée »."""
    en_chaine = [*EN_COURS, Statut.PROVISOIRE.value]
    for ligne in frappe.get_all(COPIE, {"statut": ["in", en_chaine], "etape_courante": ["is", "not set"]},
                                ["name", "soumission", "version"]):
        if frappe.db.exists(COPIE, {"soumission": ligne.soumission, "version": [">", ligne.version]}):
            frappe.db.set_value(COPIE, ligne.name, "statut", Statut.REMPLACEE.value, update_modified=False)


CHAMPS_COPIE = ["name", "apprenant", "exercice", "cohorte", "type_exercice", "version", "statut"]
CHAMPS_ETAT = ["etape_courante", "echeance", "escalade_a", "butoir", "souffrance_depuis", "rappel_souffrance"]


def _date(valeur):
    return get_datetime(valeur) if valeur else None


def _etat(ligne) -> Etat:
    return Etat(ligne.etape_courante or "", _date(ligne.echeance), ligne.escalade_a or "", _date(ligne.butoir),
                _date(ligne.souffrance_depuis), _date(ligne.rappel_souffrance))


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

    def echeance(self, exercice: str):
        """Fin de la période de rendu du devoir LMS, s'il en a une."""
        fin = frappe.db.get_value("LMS Assignment", exercice, "schedule_end")
        return get_datetime(fin) if fin else None

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
            "source_url": contenu.source_url, "commit": contenu.commit, "instantane": contenu.instantane.value,
            "depose_le": contenu.depose_le,
        }).insert(ignore_permissions=True).name

    def contenu(self, copie_id: str) -> Contenu:
        ligne = frappe.db.get_value(COPIE, copie_id, ["contenu", "source_url", "commit", "signature", "soumission",
                                                      "instantane", "depose_le"], as_dict=True)
        return Contenu(ligne.contenu or "", ligne.source_url or "", ligne.commit or "", ligne.signature or "",
                       ligne.soumission or "", EtatInstantane(ligne.instantane or ""),
                       get_datetime(ligne.depose_le) if ligne.depose_le else None)

    def completer_contenu(self, copie_id: str, texte: str, commit: str, instantane: EtatInstantane) -> None:
        frappe.db.set_value(COPIE, copie_id, {"contenu": texte, "commit": commit, "instantane": instantane.value})

    def rendus_depuis(self, apprenant: str, depuis) -> int:
        """Copies créées pour l'apprenant depuis cette date (heure du site) : débit de rendus."""
        return frappe.db.count(COPIE, {"apprenant": apprenant, "creation": [">=", depuis]})

    def instantanes_en_attente(self, avant) -> list[str]:
        """Dépôts à photographier, déposés au plus tard à cette date (UTC) ; une version remplacée ne l'est
        jamais : de rendus rapprochés, seul le dernier est photographié."""
        filtres = {"instantane": EtatInstantane.EN_COURS.value, "statut": ["!=", Statut.REMPLACEE.value],
                   "depose_le": ["<=", avant]}
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="depose_le")

    def cours(self, exercice: str) -> str | None:
        return frappe.db.get_value("LMS Assignment", exercice, "course")

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

    def courante(self, copie_id: str) -> bool:
        """Lecture verrouillante de la dernière version de la soumission : voit un rendu validé entre-temps."""
        soumission = frappe.db.get_value(COPIE, copie_id, "soumission")
        derniere = self.version_courante(soumission, verrouillee=True)
        return derniere is not None and derniere.id == copie_id

    def versions(self, copie_id: str) -> list[dict]:
        """Versions antérieures de la même soumission, de la plus ancienne à la plus récente."""
        soumission, version = frappe.db.get_value(COPIE, copie_id, ["soumission", "version"])
        lignes = frappe.get_all(COPIE, {"soumission": soumission, "version": ["<", version]},
                                ["name", "version", "creation"], order_by="version")
        return [{"copie": ligne.name, "version": int(ligne.version), "rendue_le": ligne.creation} for ligne in lignes]

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

    def marquer_souffrance(self, copie_id: str, depuis) -> None:
        frappe.db.set_value(COPIE, copie_id, {"en_souffrance": 1, "souffrance_depuis": depuis,
                                              "rappel_souffrance": depuis})

    def rappeler_souffrance(self, copie_id: str, quand) -> None:
        frappe.db.set_value(COPIE, copie_id, "rappel_souffrance", quand)

    def lever_souffrance(self, copie_id: str) -> None:
        frappe.db.set_value(COPIE, copie_id, {"en_souffrance": 0, "souffrance_depuis": None,
                                              "rappel_souffrance": None})

    # --- réservation de la pré-correction : marque courte, validée aussitôt ---------------------
    def reserver_ia(self, copie_id: str, maintenant, peremption) -> bool:
        """Sous un verrou court : ni proposition IA, ni marque vivante -> marque posée. La transaction est validée
        aussitôt : aucun verrou n'est tenu pendant l'appel au modèle."""
        marque = frappe.db.get_value(COPIE, copie_id, "ia_reservee_le", for_update=True)
        deja = frappe.db.exists(PROPOSITION, {"copie": copie_id, "source": Source.IA.value})
        libre = not deja and (not marque or get_datetime(marque) <= maintenant - peremption)
        if libre:
            frappe.db.set_value(COPIE, copie_id, "ia_reservee_le", maintenant)
        frappe.db.commit()
        return libre

    def liberer_ia(self, copie_id: str) -> None:
        frappe.db.set_value(COPIE, copie_id, "ia_reservee_le", None)
        frappe.db.commit()

    def copies_en_souffrance(self) -> list[str]:
        return frappe.get_all(COPIE, {"en_souffrance": 1}, pluck="name", order_by="souffrance_depuis")

    def souffrances(self) -> list[tuple[Copie, Etat]]:
        """Copies en souffrance encore dans la chaîne, la plus ancienne d'abord."""
        lignes = frappe.get_all(COPIE, {"en_souffrance": 1, "statut": ["in", EN_COURS]}, CHAMPS_COPIE + CHAMPS_ETAT,
                                order_by="souffrance_depuis")
        return [(_copie(ligne), _etat(ligne)) for ligne in lignes]

    def copies_en_cours(self) -> list[CopieEnCours]:
        """Copies encore dans la chaîne (avec une étape), et le YAML de leur exercice : périmètre du simulateur."""
        lignes = frappe.get_all(COPIE, {"statut": ["in", EN_COURS], "etape_courante": ["is", "set"]}, CHAMPS_COPIE,
                                order_by="creation")
        exercices = {x: self.exercice(x) for x in {ligne.exercice for ligne in lignes}}
        return [CopieEnCours(ligne.name, TypeExercice(ligne.type_exercice), ligne.cohorte or None, ligne.exercice,
                             exercices[ligne.exercice].chaine if exercices[ligne.exercice] else None)
                for ligne in lignes]

    def fixer_butoir(self, copie_id: str, butoir) -> None:
        frappe.db.set_value(COPIE, copie_id, "butoir", butoir)

    def titulaires(self, copie_id: str) -> set[str]:
        return set(self.equipe(copie_id).titulaires)

    def equipe(self, copie_id: str) -> EquipeEffective:
        """Équipe de correction de la copie (exercice > cohorte > cours > globale, champ par champ) ; titulaires
        par défaut : formateurs de la cohorte, sinon du cours, sinon le formateur des réglages OpenLab Academy."""
        cohorte, exercice = frappe.db.get_value(COPIE, copie_id, ["cohorte", "exercice"])
        return self.equipe_de(exercice, cohorte or None)

    def equipe_de(self, exercice: str, cohorte: str | None) -> EquipeEffective:
        cours = frappe.db.get_value("LMS Assignment", exercice, "course") or ""
        return resoudre_equipe(reglages_evaluation_frappe.equipes(), cours or None, cohorte or None, exercice,
                               self._formateurs(cohorte, cours))

    @staticmethod
    def _formateurs(cohorte: str | None, cours: str) -> tuple[str, ...]:
        noms = frappe.get_all(INSTRUCTEUR, {"parent": cohorte or "", "parenttype": "LMS Batch"},
                              pluck="instructor", parent_doctype="LMS Batch")
        if not noms:
            noms = frappe.get_all(INSTRUCTEUR, {"parent": cours, "parenttype": "LMS Course"},
                                  pluck="instructor", parent_doctype="LMS Course")
        if not noms:
            noms = [frappe.db.get_single_value("Reglages OpenLab Academy", "formateur")]
        return tuple(sorted({n for n in noms if n}))

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
            if ou is not None:
                return frappe.get_all(COPIE, filtres, or_filters=ou, pluck="name", order_by="creation")
        return frappe.get_all(COPIE, filtres, pluck="name", order_by="creation")

    @staticmethod
    def _perimetre(personnes: list[str]) -> list[list] | None:
        """Filtres « ou » des copies que ces personnes peuvent corriger ; None : toutes (équipe globale)."""
        def parents(table, parent, filtres):
            return frappe.get_all(table, {**filtres, "parenttype": parent}, pluck="parent", parent_doctype=parent)
        lots = parents(INSTRUCTEUR, "LMS Batch", {"instructor": ["in", personnes]})
        cours = parents(INSTRUCTEUR, "LMS Course", {"instructor": ["in", personnes]})
        exercices = []
        equipes = frappe.get_all("Equipe Correction OpenLab", {"name": ["in", parents(
            "Membre Equipe OpenLab", "Equipe Correction OpenLab", {"utilisateur": ["in", personnes],
                                                                     "role": "titulaire"})]},
                                 ["cours", "cohorte", "exercice"]) if personnes else []
        for e in equipes:  # titulaires d'une équipe de correction : sa cible ; l'équipe globale voit tout
            if not (e.cours or e.cohorte or e.exercice):
                return None
            (exercices if e.exercice else lots if e.cohorte else cours).append(e.exercice or e.cohorte or e.cours)
        evaluateurs = frappe.get_all("Course Evaluator", {"evaluator": ["in", personnes]}, pluck="name")
        if evaluateurs:  # jurés : évaluateurs des cours du lot
            lots += parents("Batch Course", "LMS Batch", {"evaluator": ["in", evaluateurs]})
        ou = [["escalade_a", "in", personnes]]
        if lots:
            ou.append(["cohorte", "in", lots])
        if cours:
            exercices += frappe.get_all("LMS Assignment", {"course": ["in", cours]}, pluck="name")
        if exercices:
            ou.append(["exercice", "in", exercices])
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
