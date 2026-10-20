"""Adaptateur : copies, propositions, relectures, grilles d'exercice et cohorte de l'apprenant dans Frappe."""
import json

import frappe

from openlab_academy.application.soumettre_copie import Contenu, Exercice
from openlab_academy.domain.copie import Copie, Proposition, Source, Statut
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Chaine, TypeExercice

COPIE = "Copie OpenLab"
PROPOSITION = "Proposition OpenLab"
RELECTURE = "Relecture Pair OpenLab"
GRILLE_EXERCICE = "Grille Exercice OpenLab"
AUTO_EVALUATION = "Auto Evaluation OpenLab"


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


def supprimer_grilles_sans_copie(exercices: list[str]) -> None:
    """Retire les grilles des exercices purgés par une republication, sauf celles qui ont des copies."""
    for exercice in exercices:
        if not frappe.db.exists(COPIE, {"exercice": exercice}):
            frappe.db.delete(GRILLE_EXERCICE, {"exercice": exercice})


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

    def version_courante(self, soumission: str) -> Copie | None:
        noms = frappe.get_all(COPIE, {"soumission": soumission}, pluck="name", order_by="version desc", limit=1)
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

    def propositions(self, copie_id: str) -> list[Proposition]:
        return [Proposition(Source(d.source), d.auteur, json.loads(d.niveaux_json or "{}"),
                            json.loads(d.commentaires_json or "{}"), json.loads(d.citations_json or "{}"),
                            d.confiance, d.au_nom_de or None)
                for d in frappe.get_all(PROPOSITION, filters={"copie": copie_id}, order_by="creation",
                                        fields=["source", "auteur", "niveaux_json", "commentaires_json",
                                                "citations_json", "confiance", "au_nom_de"])]

    def annuler_relectures(self, copie_id: str) -> None:
        for nom in frappe.get_all(RELECTURE, {"copie": copie_id, "statut": "à_faire"}, pluck="name"):
            frappe.db.set_value(RELECTURE, nom, "statut", "annulée")

