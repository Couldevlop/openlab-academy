"""Cas d'usage : orchestration de la chaîne de correction. Rien ne bloque une copie.

`FaireAvancer` fait passer une copie à son étape active suivante et la déclenche : contrôles et pré-correction
partent en tâche de fond (la pré-correction tourne pendant que les pairs relisent), les pairs sont attribués,
le jury et le formateur sont attendus. `TraiterEcheances` applique, chaque heure, l'action réglée à toute étape
ou relecture échue, et journalise chaque action automatique au nom du système.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from openlab_academy.application.pairs import AttribuerPairs, DepotRelectures, Relecture, StatutRelecture
from openlab_academy.application.soumettre_copie import DepotCopies
from openlab_academy.domain.copie import Copie, Statut, etape_suivante, nb_pairs_possible
from openlab_academy.domain.echeances import escalade
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, Chaine, Etape, Expiration, ReglagesEvaluation, Surcharge)

SYSTEME = "systeme"
TACHES = {Etape.CONTROLES: "controler", Etape.IA: "pre_corriger"}
TERMINEES = (Statut.RENVOYEE, Statut.PROVISOIRE, Statut.PUBLIEE)


@dataclass(frozen=True)
class Etat:
    """Où en est la copie dans sa chaîne : étape courante, échéance, destinataire d'une escalade."""

    etape: str
    echeance: datetime | None
    escalade_a: str = ""


class DepotChaine(DepotCopies, Protocol):
    def verrouiller(self, copie_id: str) -> None: ...  # sérialise les avancées concurrentes d'une même copie
    def etat(self, copie_id: str) -> Etat: ...
    def grille(self, copie_id: str) -> Grille: ...
    def copies_echues(self, maintenant: datetime) -> list[str]: ...
    def escalader(self, copie_id: str, destinataire: str, echeance: datetime) -> None: ...
    def titulaires(self, copie_id: str) -> set[str]: ...


class SourceReglages(Protocol):
    def reglages(self) -> ReglagesEvaluation: ...
    def surcharges(self) -> tuple[Surcharge, ...]: ...


Journal = Callable[[str, str, str, dict, dict], None]


def chaine_de(copie: Copie, depot: DepotCopies, source: SourceReglages) -> Chaine:
    """Chaîne effective de la copie ; une surcharge devenue dangereuse ne bloque pas : la chaîne du type s'applique."""
    reglages = source.reglages()
    exercice = depot.exercice(copie.exercice)
    try:
        return reglages.chaine_pour(copie.type_, copie.cohorte or None, copie.exercice, source.surcharges(),
                                    exercice.chaine if exercice else None)
    except ReglagesInvalides:
        return reglages.chaines.get(copie.type_) or CHAINES_DEFAUT[copie.type_]


def suppleant_de(copie: Copie, surcharges: tuple[Surcharge, ...]) -> str | None:
    """Suppléant du formateur, réglé sur la surcharge de la cohorte."""
    return next((s.suppleant for s in surcharges
                 if s.exercice is None and s.cohorte == copie.cohorte and s.suppleant), None)


def _statut(actuel: Statut, quittee: Etape | None, etape: Etape) -> Statut:
    if etape == Etape.PAIRS:
        return Statut.EN_RELECTURE
    if etape in (Etape.JURY, Etape.FORMATEUR):
        return Statut.A_CORRIGER
    if quittee == Etape.CONTROLES:
        return Statut.CONTROLEE
    return actuel


class FaireAvancer:
    def __init__(self, depot: DepotChaine, relectures: DepotRelectures, source: SourceReglages,
                 horloge: Callable[[], datetime], file: Callable[[str, str], None], journal: Journal = lambda *_: None):
        self._depot = depot
        self._relectures = relectures
        self._source = source
        self._horloge = horloge
        self._file = file
        self._journal = journal

    def chaine(self, copie: Copie) -> Chaine:
        return chaine_de(copie, self._depot, self._source)

    def pairs_requis(self, copie: Copie) -> int:
        return self._requis(copie, self.chaine(copie))

    def _requis(self, copie: Copie, chaine: Chaine) -> int:
        return nb_pairs_possible(chaine.nb_pairs, self._relectures.taille_cohorte(copie.cohorte))

    def demarrer(self, copie_id: str) -> None:
        """Copie tout juste rendue : l'auto-évaluation est déjà faite, sinon la première étape est déclenchée."""
        etape = Etape(self._depot.etat(copie_id).etape)
        if etape == Etape.AUTO_EVALUATION:
            self.executer(copie_id, etape)
            return
        copie = self._depot.copie(copie_id)
        self._entrer(copie, None, etape, self.chaine(copie))

    def accepte_resultat(self, copie_id: str, etape: Etape) -> bool:
        """Un résultat d'étape est-il encore à consigner ? La pré-correction, lancée en parallèle des pairs,
        reste utile jusqu'à la publication ; les autres étapes ne valent que tant qu'elles sont courantes.
        Une version remplacée (sans étape) n'accepte plus rien."""
        etat = self._depot.etat(copie_id)
        if etape == Etape.IA:
            return bool(etat.etape) and self._depot.copie(copie_id).statut not in TERMINEES
        return etat.etape == etape.value

    def executer(self, copie_id: str, terminee: Etape | None = None) -> None:
        """Passe à l'étape active suivante ; un signal d'une étape qui n'est plus la courante est ignoré."""
        self._depot.verrouiller(copie_id)  # un second signal concurrent relira l'étape déjà avancée
        copie = self._depot.copie(copie_id)
        etat = self._depot.etat(copie_id)
        if copie.statut in TERMINEES or not etat.etape:  # terminée, ou version remplacée
            return
        courante = Etape(etat.etape)
        if courante == Etape.FORMATEUR or terminee not in (None, courante):
            return
        chaine = self.chaine(copie)
        if courante == Etape.PAIRS:
            self._depot.annuler_relectures(copie_id)  # la copie avance avec les relectures obtenues
        self._entrer(copie, courante, etape_suivante(chaine, courante), chaine)

    def _entrer(self, copie: Copie, quittee: Etape | None, etape: Etape, chaine: Chaine) -> None:
        requis = self._requis(copie, chaine)
        if etape == Etape.PAIRS and requis == 0:
            self._journal(copie.id, SYSTEME, "pairs sautés", {}, {"cohorte": copie.cohorte})
            self._entrer(copie, quittee, etape_suivante(chaine, etape), chaine)
            return
        statut = _statut(copie.statut, quittee, etape)
        if statut != copie.statut:
            copie = copie.passer_a(statut)
        delai = chaine.config(etape).delai_heures
        self._depot.changer_statut(copie.id, copie.statut, etape.value, self._horloge() + timedelta(hours=delai))
        self._journal(copie.id, SYSTEME, "étape suivante", {"etape": quittee.value if quittee else ""},
                      {"etape": etape.value})
        if etape in TACHES:
            self._file(TACHES[etape], copie.id)
        if etape == Etape.IA and etape_suivante(chaine, etape) == Etape.PAIRS and requis > 0:
            self._entrer(copie, etape, Etape.PAIRS, chaine)  # la pré-correction tourne pendant les relectures
        elif etape == Etape.PAIRS:
            AttribuerPairs(self._relectures, self._horloge).executer(
                copie, self._relectures.copies_rendues(copie.exercice, copie.cohorte), requis, delai)


class TraiterEcheances:
    def __init__(self, depot: DepotChaine, relectures: DepotRelectures, source: SourceReglages,
                 avancer: FaireAvancer, horloge: Callable[[], datetime], journal: Journal = lambda *_: None,
                 isoler: Callable[[Callable[[], None]], None] = lambda action: action(),
                 notifier: Callable[[str, str], None] = lambda *_: None):
        self._depot = depot
        self._relectures = relectures
        self._source = source
        self._avancer = avancer
        self._horloge = horloge
        self._journal = journal
        self._isoler = isoler  # une copie en erreur n'empêche pas de traiter les autres
        self._notifier = notifier

    def executer(self) -> None:
        maintenant = self._horloge()
        for r in self._relectures.relectures_echues(maintenant):
            self._isoler(lambda r=r: self._relecture(r, maintenant))
        for copie_id in self._depot.copies_echues(maintenant):
            self._isoler(lambda copie_id=copie_id: self._copie(copie_id, maintenant))

    # --- relecture échue : rappel, puis réattribuée ou annulée, le relecteur en retard étant dispensé ---
    def _relecture(self, r: Relecture, maintenant: datetime) -> None:
        self._depot.verrouiller(r.copie)
        r = self._relectures.verrouiller_relecture(r.id)
        if r.statut != StatutRelecture.A_FAIRE or r.echeance is None or r.echeance > maintenant:
            return  # relue ou déjà traitée entre-temps
        copie = self._depot.copie(r.copie)
        config = self._avancer.chaine(copie).config(Etape.PAIRS)
        if not r.rappelee:
            echeance = maintenant + timedelta(hours=config.delai_heures)
            self._relectures.rappeler(r.id, echeance)
            self._notifier(r.relecteur, f"Rappel : une relecture vous attend, à rendre avant le "
                                        f"{echeance:%d/%m/%Y à %H:%M}. Passé ce délai, elle sera retirée.")
            self._journal(copie.id, SYSTEME, "rappel de relecture", {"echeance": r.echeance},
                          {"echeance": echeance})
            return
        rendues = self._relectures.copies_rendues(copie.exercice, copie.cohorte)
        nouveau = None
        if config.expiration == Expiration.REATTRIBUER:
            nouveau = AttribuerPairs(self._relectures, self._horloge).reattribuer(copie, rendues, config.delai_heures)
        if nouveau:
            self._relectures.changer_statut_relecture(r.id, StatutRelecture.REATTRIBUEE)
            self._journal(copie.id, SYSTEME, "relecture réattribuée", {"relecteur": r.relecteur},
                          {"relecteur": nouveau})
        else:
            self._relectures.changer_statut_relecture(r.id, StatutRelecture.ANNULEE)
            self._journal(copie.id, SYSTEME, "relecture annulée", {"relecteur": r.relecteur}, {})
        for sienne in rendues:
            if sienne.apprenant == r.relecteur:
                self._relectures.dispenser(sienne.id)
                self._journal(sienne.id, SYSTEME, "relectures dispensées", {}, {"relecture": r.id})

    # --- étape échue -------------------------------------------------------------------------------
    def _copie(self, copie_id: str, maintenant: datetime) -> None:
        """L'échéance enregistrée à l'entrée dans l'étape fait foi ; l'action est celle réglée pour l'étape."""
        self._depot.verrouiller(copie_id)
        copie = self._depot.copie(copie_id)
        etat = self._depot.etat(copie_id)
        if (copie.statut in TERMINEES or not etat.etape or etat.echeance is None
                or etat.echeance > maintenant):
            return  # l'étape a changé depuis la sélection : elle n'est plus échue
        etape = Etape(etat.etape)
        chaine = self._avancer.chaine(copie)
        action = chaine.config(etape).expiration
        if etape == Etape.FORMATEUR:
            self._formateur(copie, etat, action, chaine.config(etape).delai_heures, maintenant)
            return
        libelle = action.value
        if etape == Etape.PAIRS and action == Expiration.REATTRIBUER:
            attente = [r.echeance for r in self._relectures.relectures(copie.exercice, copie.cohorte)
                       if r.copie == copie_id and r.statut == StatutRelecture.A_FAIRE
                       and r.echeance and r.echeance > maintenant]
            if attente:
                self._depot.changer_statut(copie_id, copie.statut, etape.value, max(attente))
                self._journal(copie_id, SYSTEME, "attente des relectures", {"echeance": etat.echeance},
                              {"echeance": max(attente)})
                return
            libelle = Expiration.PASSER.value  # personne d'autre : la copie avance avec les relectures obtenues
        self._journal(copie_id, SYSTEME, libelle, {"etape": etape.value}, {})
        self._avancer.executer(copie_id, etape)

    def _formateur(self, copie: Copie, etat: Etat, action: Expiration, delai: int, maintenant: datetime) -> None:
        """Formateur échu : suppléant, puis responsable pédagogique, puis publication provisoire si elle est permise."""
        reglages = self._source.reglages()
        if action == Expiration.PUBLIER_PROVISOIRE and reglages.publication_provisoire:
            self._provisoire(copie)
            return
        responsable = reglages.responsable_pedagogique
        if not etat.escalade_a:
            suivant = escalade(Etape.FORMATEUR, suppleant_de(copie, self._source.surcharges()), responsable)
            avant = sorted(self._depot.titulaires(copie.id))
        else:
            suivant = responsable if etat.escalade_a != responsable else ""
            avant = [etat.escalade_a]
        if suivant:
            self._depot.escalader(copie.id, suivant, maintenant + timedelta(hours=delai))
            self._journal(copie.id, SYSTEME, "escalader", {"correcteurs": avant}, {"correcteurs": [suivant]})
        elif reglages.publication_provisoire:
            self._provisoire(copie)
        else:
            self._depot.changer_statut(copie.id, copie.statut, Etape.FORMATEUR.value, None)
            self._journal(copie.id, SYSTEME, "escalade épuisée", {"correcteurs": avant}, {"correcteurs": avant})

    def _provisoire(self, copie: Copie) -> None:
        self._depot.changer_statut(copie.id, copie.passer_a(Statut.PROVISOIRE).statut, Etape.FORMATEUR.value, None)
        self._journal(copie.id, SYSTEME, "publication provisoire", {"statut": copie.statut.value},
                      {"statut": Statut.PROVISOIRE.value})
