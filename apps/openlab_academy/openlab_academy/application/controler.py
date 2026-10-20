"""Cas d'usage : contrôles automatiques d'une copie (longueur, lien et contenu du dépôt rendu).

Un échec bloquant renvoie la copie à l'apprenant, motifs à l'appui, avant toute autre étape. Un contrôleur
indisponible (réseau, délai, API) ne bloque rien : l'étape est marquée « non disponible » et la copie avance.
Le travail lent se fait avant toute lecture verrouillante : le verrou de la copie n'est pris que pour consigner.
"""
from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from openlab_academy.application.chaine import SYSTEME, DepotChaine, Journal
from openlab_academy.application.soumettre_copie import Contenu, Instantane
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
    def completer_contenu(self, copie_id: str, texte: str, commit: str) -> None: ...


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
                 journal: Journal = lambda *_: None, notifier: Callable[[str, str], None] = lambda *_: None,
                 instantane: Instantane | None = None):
        self._depot = depot
        self._instantane = instantane
        self._controleur = controleur
        self._avancer = avancer
        self._journal = journal
        self._notifier = notifier

    def executer(self, copie_id: str) -> None:
        try:
            avant = self._depot.contenu(copie_id)
            contenu = self._reprendre(avant)
            motifs = self._controleur.verifier(self._depot.copie(copie_id), self._depot.grille(copie_id), contenu)
        except Exception as erreur:  # rien ne bloque : l'étape est marquée non disponible
            consigner_indisponibilite(self._avancer, self._journal, copie_id, Etape.CONTROLES,
                                      "contrôles non disponibles", erreur)
            return
        if not self._avancer.accepte_resultat(copie_id, Etape.CONTROLES):
            return
        if contenu != avant:  # instantané repris : figé avec le résultat des contrôles
            self._depot.completer_contenu(copie_id, contenu.texte, contenu.commit)
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

    def _reprendre(self, contenu: Contenu) -> Contenu:
        """Un rendu en URL sans instantané (hébergeur injoignable au rendu) est photographié maintenant : pairs et
        formateur travaillent sur un commit figé, jamais sur le dépôt vivant. Une indisponibilité remonte (étape
        « non disponible ») ; un défaut du dépôt laisse le contrôleur le constater et en faire un motif."""
        if self._instantane is None or not contenu.rendu_par_lien or contenu.texte.strip():
            return contenu
        try:
            texte, commit = self._instantane.prendre(contenu.source_url)
        except EtapeIndisponible:
            raise
        except Exception:
            return contenu
        return replace(contenu, texte=texte, commit=commit)
