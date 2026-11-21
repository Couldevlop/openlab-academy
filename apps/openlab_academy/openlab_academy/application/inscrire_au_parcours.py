"""Cas d'usage : s'inscrire à un parcours depuis le site public.

Le visiteur n'envoie **qu'un nom de parcours**. Il ne choisit pas sa cohorte, ne dit pas si le parcours
est gratuit, ne fournit pas de tarif : tout cela est relu ici. Un formulaire bricolé ne peut donc rien
obtenir de plus qu'un formulaire honnête, et la barrière la plus solide est la signature elle-même —
`executer` ne prend pas de cohorte, on ne falsifie pas un paramètre qui n'existe pas.

Ce module ne crée aucun dossier de paiement : il n'en a pas besoin. L'inscription à la cohorte en ouvre un
toute seule, par les `doc_events` de `LMS Batch Enrollment`. Le redire ici en ferait deux.

L'offre montrée et l'inscription faite passent par le même calcul (`_examiner`) : une page qui annonce
« ouvert » et une inscription qui refuse, c'est un visiteur perdu ; l'inverse, c'est une place vendue deux
fois.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from openlab_academy.application.acces_parcours import redirection_paiement
from openlab_academy.domain.inscription_ouverte import (Candidate, Etat, cohorte_d_accueil, etat_du_parcours)

LIEN_PARCOURS = "/lms/courses/{}"
SANS_TARIF = Etat.FERMEE_RETIREE  # un parcours payant sans prix n'est pas une offre : il n'est pas prêt


class InscriptionImpossible(Exception):
    """L'inscription ne peut pas aboutir ; le message est destiné au visiteur."""


class Cohortes(Protocol):
    def candidates(self, cours: str) -> tuple[Candidate, ...]:
        """Les cohortes du parcours, vues sous l'angle des inscriptions."""


class Inscripteur(Protocol):
    def deja_inscrit(self, apprenant: str, cours: str) -> bool: ...
    def a_la_cohorte(self, apprenant: str, cohorte: str, cours: str) -> None: ...
    def au_parcours(self, apprenant: str, cours: str) -> None: ...


class Gratuits(Protocol):
    def gratuit(self, cours: str) -> bool: ...


class Tarifs(Protocol):
    def montant(self, cours: str) -> int | None:
        """Prix du parcours en francs CFA, ou None s'il n'en a pas encore."""


class Reglages(Protocol):
    def inscription_tardive_mois(self) -> int: ...

    def inscriptions_suspendues(self) -> bool:
        """Vrai tant que la façade publique ne prend aucune inscription."""


@dataclass(frozen=True)
class Offre:
    """Ce que la page du parcours montre. Rien de plus que ce qu'un visiteur a besoin de voir.

    L'identifiant de la cohorte n'y est pas : son titre s'affiche, son nom technique reste au serveur. Ce
    que le client ne connaît pas, il ne peut pas le falsifier.
    """
    etat: Etat
    gratuit: bool
    deja_inscrit: bool
    session: str = ""
    debut: str = ""
    fin: str = ""
    places_restantes: int = 0
    montant: int | None = None

    def en_dict(self) -> dict:
        """La forme qui part en JSON vers la page : des valeurs simples, et elles seules."""
        return {
            "etat": self.etat.name,
            "message": self.etat.message,
            "ouverte": self.etat.ouverte,
            "gratuit": self.gratuit,
            "deja_inscrit": self.deja_inscrit,
            "session": self.session,
            "debut": self.debut,
            "fin": self.fin,
            "places_restantes": self.places_restantes,
            "montant": self.montant,
        }


class InscrireAuParcours:
    def __init__(self, cohortes: Cohortes, inscripteur: Inscripteur, gratuits: Gratuits, tarifs: Tarifs,
                 reglages: Reglages, aujourd_hui: Callable[[], date]):
        self._cohortes = cohortes
        self._inscripteur = inscripteur
        self._gratuits = gratuits
        self._tarifs = tarifs
        self._reglages = reglages
        self._aujourd_hui = aujourd_hui

    def _examiner(self, cours: str) -> tuple[Etat, Candidate | None, bool, int | None]:
        """Le calcul unique : état, cohorte d'accueil, gratuité, montant.

        La suspension passe avant tout le reste, et notamment avant la gratuité : un parcours gratuit
        s'ouvre sans cohorte ni tarif, il serait donc la seule porte restée ouverte sur une façade qui
        n'en veut aucune. Elle passe aussi avant l'absence de tarif, pour que le visiteur lise la vraie
        raison et non « pas encore ouvert ».

        Un parcours gratuit s'ouvre sans cohorte ni prix — un MOOC n'a pas de promotion. Un parcours
        payant sans tarif n'est pas proposé : `OuvrirDossier.verifier` le refuserait plus loin
        (`TarifAbsent`), autant ne pas l'annoncer ouvert.
        """
        if self._reglages.inscriptions_suspendues():
            return Etat.SUSPENDUE, None, False, None
        if self._gratuits.gratuit(cours):
            return Etat.OUVERTE, None, True, None
        montant = self._tarifs.montant(cours)
        if montant is None:
            return SANS_TARIF, None, False, None
        aujourd_hui = self._aujourd_hui()
        mois = self._reglages.inscription_tardive_mois()
        candidates = self._cohortes.candidates(cours)
        accueil = cohorte_d_accueil(candidates, aujourd_hui, mois)
        if accueil is None:
            return etat_du_parcours(candidates, aujourd_hui, mois), None, False, montant
        return Etat.OUVERTE, accueil, False, montant

    def offre(self, cours: str, apprenant: str) -> Offre:
        """Ce que montre la page. Une lecture, et rien d'autre : afficher une page n'écrit jamais rien —
        un robot d'indexation qui la parcourt ne doit inscrire personne."""
        etat, accueil, gratuit, montant = self._examiner(cours)
        deja = bool(apprenant) and self._inscripteur.deja_inscrit(apprenant, cours)
        if accueil is None:
            return Offre(etat=etat, gratuit=gratuit, deja_inscrit=deja, montant=montant)
        return Offre(etat=etat, gratuit=gratuit, deja_inscrit=deja, session=accueil.titre,
                     debut=accueil.debut.isoformat(), fin=accueil.fin.isoformat(),
                     places_restantes=accueil.places_restantes, montant=montant)

    def executer(self, cours: str, apprenant: str) -> str:
        """Inscrit, et renvoie où aller ensuite. Lève `InscriptionImpossible` avec ce qu'il faut dire.

        Le refus d'un visiteur sans compte est un garde-fou de dernier recours : la page ne montre le
        bouton qu'aux connectés, mais l'API ne s'y fie pas.
        """
        if not apprenant:
            raise InscriptionImpossible("Connectez-vous pour vous inscrire.")
        if self._inscripteur.deja_inscrit(apprenant, cours):
            return self._destination(cours, gratuit=self._gratuits.gratuit(cours))
        etat, accueil, gratuit, _ = self._examiner(cours)
        if not etat.ouverte:
            raise InscriptionImpossible(etat.message)
        if gratuit:
            self._inscripteur.au_parcours(apprenant, cours)
        else:
            self._inscripteur.a_la_cohorte(apprenant, accueil.identifiant, cours)
        return self._destination(cours, gratuit)

    @staticmethod
    def _destination(cours: str, gratuit: bool) -> str:
        """Au cours pour un parcours gratuit, au paiement pour un parcours payant — c'est là que se
        trouve la suite, et le dossier vient d'y naître."""
        return LIEN_PARCOURS.format(cours) if gratuit else redirection_paiement(cours)
