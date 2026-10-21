"""Cas d'usage : pré-correction d'une copie par le modèle souverain (proposition soumise au formateur).

La copie est une donnée non fiable, lue en texte lisible (celui que voient le formateur et les pairs) : une
tentative d'instruction au modèle écarte la pré-correction et signale la copie au formateur. Sinon le modèle
reçoit grille, consigne et copie encadrée ; sa réponse n'est retenue qu'après les garde-fous du domaine. Toute défaillance marque l'étape « non disponible » et la copie avance.
L'appel au modèle (plusieurs minutes sur CPU) précède toute lecture verrouillante de la copie.
"""
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, Journal
from openlab_academy.application.controler import (
    Avanceur, DepotControles, EtapeIndisponible, consigner_indisponibilite)
from openlab_academy.domain.copie import Proposition
from openlab_academy.domain.garde_fous_ia import construire_messages, detecter_injection, interpreter
from openlab_academy.domain.reglages_evaluation import Etape, ReglagesEvaluation

SIGNALEMENT = "copie signalée : tentative d'instruction à l'IA"


class CorrecteurIA(Protocol):
    def proposer(self, messages: list[dict], modele: str) -> str: ...


class DepotPreCorrection(DepotControles, Protocol):
    def consigne(self, exercice: str) -> str: ...
    def texte_lisible(self, copie_id: str) -> str: ...


class PreCorriger:
    def __init__(self, depot: DepotPreCorrection, correcteur: CorrecteurIA, reglages: ReglagesEvaluation,
                 avancer: Avanceur, journal: Journal = lambda *_: None):
        self._depot = depot
        self._correcteur = correcteur
        self._ia = reglages.ia
        self._avancer = avancer
        self._journal = journal

    def executer(self, copie_id: str) -> None:
        try:
            action, details, proposition = self._proposer(copie_id)
        except Exception as erreur:  # rien ne bloque : l'étape est marquée non disponible
            consigner_indisponibilite(self._avancer, self._journal, copie_id, Etape.IA,
                                      "pré-correction non disponible", erreur)
            return
        self._conclure(copie_id, action, details, proposition)

    def _proposer(self, copie_id: str) -> tuple[str, dict, Proposition | None]:
        contenu = self._depot.contenu(copie_id)
        texte = self._depot.texte_lisible(copie_id)  # balises et entités d'un rendu LMS ne masquent rien
        tournures = detecter_injection(texte, self._ia.tournures_injection)
        if tournures:  # proposition écartée, copie signalée au formateur
            return SIGNALEMENT, {"tournures": list(tournures)}, None
        modele = self._ia.modele_code if contenu.rendu_par_lien else self._ia.modele_texte
        if not (self._ia.url and modele):
            raise EtapeIndisponible("IA non configurée (URL ou modèle)")
        if not texte.strip():
            raise EtapeIndisponible("copie vide")
        copie, grille = self._depot.copie(copie_id), self._depot.grille(copie_id)
        messages = construire_messages(grille, self._depot.consigne(copie.exercice), texte)
        proposition = interpreter(self._correcteur.proposer(messages, modele), grille, texte)
        return "pré-correction proposée", {"modele": modele, "confiance": proposition.confiance}, proposition

    def _conclure(self, copie_id: str, action: str, details: dict, proposition=None) -> None:
        """En parallèle des pairs, le résultat est consigné sans faire avancer la copie (étape non courante)."""
        if not self._avancer.accepte_resultat(copie_id, Etape.IA):
            return
        if proposition is not None:
            self._depot.ajouter_proposition(copie_id, proposition)
        self._journal(copie_id, SYSTEME, action, {}, details)
        self._avancer.executer(copie_id, Etape.IA)
