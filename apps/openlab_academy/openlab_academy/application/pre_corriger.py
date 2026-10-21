"""Cas d'usage : pré-correction d'une copie par le modèle souverain (proposition soumise au formateur).

La copie est une donnée non fiable, lue en texte lisible (celui que voient le formateur et les pairs) : une
tentative d'instruction au modèle écarte la pré-correction et signale la copie au formateur. Sinon le modèle
reçoit grille, consigne et copie encadrée ; sa réponse n'est retenue qu'après les garde-fous du domaine. Une
copie dont le prompt dépasserait le contexte du modèle n'est jamais tronquée ni envoyée. Toute défaillance
marque l'étape « non disponible » et la copie avance.
L'appel au modèle (plusieurs minutes sur CPU) se fait sans aucun verrou tenu : une marque courte sur la copie,
validée aussitôt, le réserve ; le résultat est consigné sous un verrou court.
"""
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, Journal
from openlab_academy.application.controler import (
    Avanceur, DepotControles, EtapeIndisponible, consigner_indisponibilite)
from openlab_academy.domain.copie import EtatInstantane, Proposition, Source
from openlab_academy.domain.garde_fous_ia import construire_messages, detecter_injection, estimer_jetons, interpreter
from openlab_academy.domain.reglages_evaluation import RESERVE_REPONSE_JETONS, Etape, ReglagesEvaluation

SIGNALEMENT = "copie signalée : tentative d'instruction à l'IA"
MARGE_TACHE_S = 60  # la tâche survit au délai de l'appel au modèle : c'est lui qui expire, proprement


class CorrecteurIA(Protocol):
    def proposer(self, messages: list[dict], modele: str) -> str: ...


class DepotPreCorrection(DepotControles, Protocol):
    def consigne(self, exercice: str) -> str: ...
    def texte_lisible(self, copie_id: str) -> str: ...
    def texte_compact(self, copie_id: str) -> str: ...  # balises retirées sans séparateur : « ign<b></b>ore »
    # réservation courte, validée aussitôt : aucun verrou n'est tenu pendant l'appel au modèle
    def reserver_ia(self, copie_id: str, maintenant: datetime, peremption: timedelta) -> bool: ...
    def liberer_ia(self, copie_id: str) -> None: ...


class PreCorriger:
    def __init__(self, depot: DepotPreCorrection, correcteur: CorrecteurIA, reglages: ReglagesEvaluation,
                 avancer: Avanceur, horloge: Callable[[], datetime], journal: Journal = lambda *_: None):
        self._depot = depot
        self._correcteur = correcteur
        self._ia = reglages.ia
        self._avancer = avancer
        self._horloge = horloge
        self._journal = journal

    def executer(self, copie_id: str) -> None:
        """Une seule pré-correction par copie : une marque courte réserve l'appel au modèle (validée aussitôt, sans
        verrou tenu pendant l'appel) ; une marque plus vieille que le délai réglé de l'IA plus la marge de la tâche
        est celle d'une tâche morte, reprise."""
        reservee = False
        try:
            if self._depot.contenu(copie_id).instantane == EtatInstantane.EN_COURS:
                return  # la tâche de l'instantané relance la pré-correction, sinon son échéance la fait passer
            peremption = timedelta(minutes=self._ia.delai_minutes, seconds=MARGE_TACHE_S)
            reservee = self._depot.reserver_ia(copie_id, self._horloge(), peremption)
            if not reservee:
                return  # proposition déjà là, ou une autre tâche (entrée dans l'étape, instantané) la prépare
            action, details, proposition = self._proposer(copie_id)
        except Exception as erreur:  # rien ne bloque : l'étape est marquée non disponible
            if reservee:
                self._depot.liberer_ia(copie_id)
            consigner_indisponibilite(self._avancer, self._journal, copie_id, Etape.IA,
                                      "pré-correction non disponible", erreur)
            return
        self._conclure(copie_id, action, details, proposition)

    def _proposer(self, copie_id: str) -> tuple[str, dict, Proposition | None]:
        contenu = self._depot.contenu(copie_id)
        texte = self._depot.texte_lisible(copie_id)  # balises et entités d'un rendu LMS ne masquent rien
        # un mot coupé par une balise vide est recollé dans le texte compact : la tournure y est cherchée aussi
        tournures = (detecter_injection(texte, self._ia.tournures_injection)
                     or detecter_injection(self._depot.texte_compact(copie_id), self._ia.tournures_injection))
        if tournures:  # proposition écartée, copie signalée au formateur
            return SIGNALEMENT, {"tournures": list(tournures)}, None
        modele = self._ia.modele_code if contenu.rendu_par_lien else self._ia.modele_texte
        if not (self._ia.url and modele):
            raise EtapeIndisponible("IA non configurée (URL ou modèle)")
        if not texte.strip():
            raise EtapeIndisponible("copie vide")
        copie, grille = self._depot.copie(copie_id), self._depot.grille(copie_id)
        messages = construire_messages(grille, self._depot.consigne(copie.exercice), texte)
        estimes, disponibles = estimer_jetons(messages), self._ia.contexte_tokens - RESERVE_REPONSE_JETONS
        if estimes > disponibles:  # jamais de troncature : la copie entière ou rien
            raise EtapeIndisponible(f"copie trop longue pour le contexte du modèle ({estimes} jetons estimés, "
                                    f"{disponibles} disponibles)")
        proposition = interpreter(self._correcteur.proposer(messages, modele), grille, texte,
                                  self._ia.citation_min_caracteres)
        return "pré-correction proposée", {"modele": modele, "confiance": proposition.confiance}, proposition

    def _conclure(self, copie_id: str, action: str, details: dict, proposition=None) -> None:
        """En parallèle des pairs, le résultat est consigné sans faire avancer la copie (étape non courante).
        Sous un verrou court (celui de `accepte_resultat`), la proposition est relue : une reprise de marque
        périmée a pu conclure entre-temps. La marque est levée dans tous les cas."""
        if self._avancer.accepte_resultat(copie_id, Etape.IA) and not (
                proposition is not None
                and any(p.source == Source.IA for p in self._depot.propositions(copie_id, verrouillee=True))):
            if proposition is not None:
                self._depot.ajouter_proposition(copie_id, proposition)
            self._journal(copie_id, SYSTEME, action, {}, details)
            self._avancer.executer(copie_id, Etape.IA)
        self._depot.liberer_ia(copie_id)
