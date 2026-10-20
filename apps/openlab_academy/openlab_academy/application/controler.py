"""Cas d'usage : contrôles automatiques d'une copie (longueur, lien et contenu du dépôt rendu).

Un échec bloquant renvoie la copie à l'apprenant, motifs à l'appui, avant toute autre étape. Un contrôleur
indisponible (réseau, délai, API) ne bloque rien : l'étape est marquée « non disponible » et la copie avance.
Le travail lent se fait avant toute lecture verrouillante : le verrou de la copie n'est pris que pour consigner.
"""
from collections.abc import Callable
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, DepotChaine, Journal
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import Copie, Proposition, Source, Statut
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import Etape


class EtapeIndisponible(Exception):
    """Un adaptateur (hébergeur de dépôts, service d'IA) n'a pas pu répondre ; son message est sûr à consigner."""


class Controleur(Protocol):
    def verifier(self, copie: Copie, grille: Grille, contenu: Contenu) -> list[str]: ...


class Avanceur(Protocol):
    def accepte_resultat(self, copie_id: str, etape: Etape) -> bool: ...
    def executer(self, copie_id: str, terminee: Etape | None = None) -> None: ...


class DepotControles(DepotChaine, Protocol):
    def contenu(self, copie_id: str) -> Contenu: ...


def cause(erreur: Exception) -> str:
    """Ce que le journal retient d'une erreur : le message d'une indisponibilité connue, sinon son seul type."""
    return str(erreur) if isinstance(erreur, EtapeIndisponible) else type(erreur).__name__


def consigner_indisponibilite(avancer: Avanceur, journal: Journal, copie_id: str, etape: Etape, libelle: str,
                              erreur: Exception) -> None:
    """Consigne l'indisponibilité si le résultat est encore attendu ; n'avance que si l'étape est la courante."""
    if not avancer.accepte_resultat(copie_id, etape):
        return  # signal périmé : la copie a quitté cette étape (ou est publiée, ou remplacée)
    journal(copie_id, SYSTEME, libelle, {}, {"etape": etape.value, "cause": cause(erreur)})
    avancer.executer(copie_id, etape)


class ControlerCopie:
    def __init__(self, depot: DepotControles, controleur: Controleur, avancer: Avanceur,
                 journal: Journal = lambda *_: None, notifier: Callable[[str, str], None] = lambda *_: None):
        self._depot = depot
        self._controleur = controleur
        self._avancer = avancer
        self._journal = journal
        self._notifier = notifier

    def executer(self, copie_id: str) -> None:
        try:
            motifs = self._controleur.verifier(self._depot.copie(copie_id), self._depot.grille(copie_id),
                                               self._depot.contenu(copie_id))
        except Exception as erreur:  # rien ne bloque : l'étape est marquée non disponible
            consigner_indisponibilite(self._avancer, self._journal, copie_id, Etape.CONTROLES,
                                      "contrôles non disponibles", erreur)
            return
        if not self._avancer.accepte_resultat(copie_id, Etape.CONTROLES):
            return
        self._depot.ajouter_proposition(copie_id, Proposition(
            Source.CONTROLES, SYSTEME, {}, {f"motif_{i}": m for i, m in enumerate(motifs, 1)}))
        if not motifs:
            self._journal(copie_id, SYSTEME, "contrôles conformes", {}, {})
            self._avancer.executer(copie_id, Etape.CONTROLES)
            return
        copie = self._depot.verrouiller(copie_id).copie
        self._depot.changer_statut(copie_id, copie.passer_a(Statut.RENVOYEE).statut, "", None)
        self._journal(copie_id, SYSTEME, "copie renvoyée", {"statut": copie.statut.value}, {"motifs": motifs})
        self._notifier(copie.apprenant, f"Votre rendu de l'exercice {copie.exercice} vous est renvoyé : "
                                        f"{' ; '.join(motifs)}. Corrigez-le puis rendez-le à nouveau.")
