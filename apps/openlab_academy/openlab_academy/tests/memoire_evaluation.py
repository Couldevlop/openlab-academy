"""Dépôts en mémoire de la chaîne de correction : copies, état d'étape, relectures, réglages."""
from dataclasses import replace
from datetime import datetime, timedelta

from openlab_academy.application.chaine import Etat
from openlab_academy.application.pairs import Relecture, StatutRelecture
from openlab_academy.application.soumettre_copie import Exercice
from openlab_academy.domain.copie import Copie, Statut, etape_suivante
from openlab_academy.domain.grille import grille_generique
from openlab_academy.domain.reglages_evaluation import ReglagesEvaluation, TypeExercice

GRILLE = grille_generique((("Pertinence", 60), ("Rigueur", 40)), ("Faible", "Moyen", "Bon"))
DEBUT = datetime(2026, 10, 20, 8, 0)
EN_COURS = {Statut.RENDUE, Statut.CONTROLEE, Statut.PRE_CORRIGEE, Statut.EN_RELECTURE, Statut.A_CORRIGER}


class SourceMemoire:
    def __init__(self, reglages=None, surcharges=()):
        self.reglages_ = reglages or ReglagesEvaluation()
        self.surcharges_ = tuple(surcharges)

    def reglages(self):
        return self.reglages_

    def surcharges(self):
        return self.surcharges_


class Memoire:
    """Implémente à la fois le dépôt des copies (chaîne) et celui des relectures."""

    def __init__(self, type_=TypeExercice.LIVRABLE, chaine=None, taille=4):
        self.exercices = {"EX1": Exercice(type_, GRILLE, chaine)}
        self.type_ = type_
        self.copies: dict[str, Copie] = {}
        self.etats: dict[str, Etat] = {}
        self.props: dict[str, list] = {}
        self.rel: dict[str, Relecture] = {}
        self.dispensees: list[str] = []
        self.tailles = {"COH1": taille}
        self.titulaires_ = {"form@x.ci"}
        self.verrous: list[str] = []
        self.paires_concurrentes: set[tuple[str, str]] = set()  # insérées par une autre transaction

    # --- préparation des cas ---------------------------------------------------
    def rendre(self, apprenant, chaine, maintenant, cohorte="COH1", exercice="EX1") -> str:
        """Ce que fait SoumettreCopie : copie rendue, première étape et son échéance."""
        cid = f"C{len(self.copies) + 1}"
        self.copies[cid] = Copie(cid, apprenant, exercice, cohorte, self.type_, 1, Statut.RENDUE)
        etape = etape_suivante(chaine, None)
        self.etats[cid] = Etat(etape.value, maintenant + timedelta(hours=chaine.config(etape).delai_heures))
        return cid

    def relectures_de(self, cid, statut=None):
        return [r for r in self.rel.values() if r.copie == cid and (statut is None or r.statut == statut)]

    def relectures_par(self, relecteur, statut=None):
        return [r for r in self.rel.values() if r.relecteur == relecteur and (statut is None or r.statut == statut)]

    # --- DepotCopies -------------------------------------------------------------
    def exercice(self, exercice):
        return self.exercices.get(exercice)

    def copie(self, copie_id):
        return self.copies[copie_id]

    def ajouter_proposition(self, copie_id, p):
        self.props.setdefault(copie_id, []).append(p)

    def propositions(self, copie_id):
        return self.props.get(copie_id, [])

    def changer_statut(self, copie_id, statut, etape, echeance):
        self.copies[copie_id] = replace(self.copies[copie_id], statut=statut)
        self.etats[copie_id] = replace(self.etats[copie_id], etape=etape, echeance=echeance)

    def annuler_relectures(self, copie_id):
        for r in self.relectures_de(copie_id, StatutRelecture.A_FAIRE):
            self.rel[r.id] = replace(r, statut=StatutRelecture.ANNULEE)

    # --- DepotChaine -------------------------------------------------------------
    def verrouiller(self, copie_id):
        self.verrous.append(copie_id)

    def etat(self, copie_id):
        return self.etats[copie_id]

    def grille(self, copie_id):
        return GRILLE

    def copies_echues(self, maintenant):
        return sorted((cid for cid, e in self.etats.items()
                       if e.echeance is not None and e.echeance <= maintenant and self.copies[cid].statut in EN_COURS),
                      key=lambda cid: self.etats[cid].echeance)

    def escalader(self, copie_id, destinataire, echeance):
        self.etats[copie_id] = replace(self.etats[copie_id], escalade_a=destinataire, echeance=echeance)

    def titulaires(self, copie_id):
        return set(self.titulaires_)

    # --- DepotRelectures ---------------------------------------------------------
    def copies_rendues(self, exercice, cohorte):
        return [c for c in self.copies.values()
                if c.exercice == exercice and c.cohorte == cohorte and c.statut != Statut.RENVOYEE]

    def taille_cohorte(self, cohorte):
        return self.tailles.get(cohorte, 0)

    def relectures(self, exercice, cohorte):
        return [r for r in self.rel.values()
                if self.copies[r.copie].exercice == exercice and self.copies[r.copie].cohorte == cohorte]

    def relecture(self, relecture_id):
        return self.rel.get(relecture_id)

    def verrouiller_relecture(self, relecture_id):
        return self.rel.get(relecture_id)

    def relectures_echues(self, maintenant):
        return [r for r in self.rel.values()
                if r.statut == StatutRelecture.A_FAIRE and r.echeance is not None and r.echeance <= maintenant]

    def attribuer(self, copie_id, relecteur, echeance):
        if (copie_id, relecteur) in self.paires_concurrentes or any(
                r.copie == copie_id and r.relecteur == relecteur for r in self.rel.values()):
            return None  # contrainte d'unicité (copie, relecteur)
        rid = f"R{len(self.rel) + 1}"
        self.rel[rid] = Relecture(rid, copie_id, relecteur, StatutRelecture.A_FAIRE, echeance)
        return rid

    def changer_statut_relecture(self, relecture_id, statut):
        self.rel[relecture_id] = replace(self.rel[relecture_id], statut=statut)

    def rappeler(self, relecture_id, echeance):
        self.rel[relecture_id] = replace(self.rel[relecture_id], rappelee=True, echeance=echeance)

    def dispenser(self, copie_id):
        self.dispensees.append(copie_id)
