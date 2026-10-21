"""Cas d'usage : orchestration de la chaîne de correction. Rien ne bloque une copie.

`FaireAvancer` fait passer une copie à son étape active suivante et la déclenche : contrôles et pré-correction
partent en tâche de fond (la pré-correction tourne pendant que les pairs relisent), les pairs sont attribués,
le jury et le formateur sont attendus. `TraiterEcheances` applique, chaque heure, l'action réglée à toute étape
ou relecture échue, et journalise chaque action automatique au nom du système.
"""
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

from openlab_academy.application.pairs import AttribuerPairs, DepotRelectures, Relecture, StatutRelecture
from openlab_academy.application.soumettre_copie import DepotCopies
from openlab_academy.domain.copie import Copie, Etat, Statut, etape_suivante, nb_pairs_possible
from openlab_academy.domain.echeances import prochain_recours
from openlab_academy.domain.equipe import EquipeEffective
from openlab_academy.domain.grille import Grille
from openlab_academy.domain.reglages_evaluation import (
    Chaine, Etape, Expiration, ReglagesEvaluation, Surcharge, reste_avant_action_souffrance)

SYSTEME = "systeme"
TACHES = {Etape.CONTROLES: "controler", Etape.IA: "pre_corriger"}
TERMINEES = (Statut.RENVOYEE, Statut.PROVISOIRE, Statut.PUBLIEE, Statut.REMPLACEE)
LIEN_CORRECTEUR = "/espace/correcteur/{}"
LIEN_RETOUR = "/espace/retour/{}"


class DepotChaine(DepotCopies, Protocol):
    def etat(self, copie_id: str) -> Etat: ...
    def grille(self, copie_id: str) -> Grille: ...
    def copies_echues(self, maintenant: datetime) -> list[str]: ...
    def escalader(self, copie_id: str, destinataire: str, echeance: datetime) -> None: ...
    def fixer_butoir(self, copie_id: str, butoir: datetime | None) -> None: ...
    def titulaires(self, copie_id: str) -> set[str]: ...
    def equipe(self, copie_id: str) -> EquipeEffective: ...  # équipe de correction résolue pour la copie
    # copie en souffrance (escalade épuisée) : marquée, rappelée chaque jour, levée une fois sortie de la chaîne
    def marquer_souffrance(self, copie_id: str, depuis: datetime) -> None: ...
    def rappeler_souffrance(self, copie_id: str, quand: datetime) -> None: ...
    def lever_souffrance(self, copie_id: str) -> None: ...
    def copies_en_souffrance(self) -> list[str]: ...
    def jures(self, copie_id: str) -> set[str]: ...


class SourceReglages(Protocol):
    def reglages(self) -> ReglagesEvaluation: ...
    def surcharges(self) -> tuple[Surcharge, ...]: ...


Journal = Callable[[str, str, str, dict, dict], None]


def chaine_de(copie: Copie, depot: DepotCopies, source: SourceReglages) -> Chaine:
    """Chaîne effective de la copie ; une surcharge devenue dangereuse ne bloque pas : la chaîne de secours
    (formateur seul) s'applique."""
    exercice = depot.exercice(copie.exercice)
    chaine, _ = source.reglages().chaine_effective(copie.type_, copie.cohorte or None, copie.exercice,
                                                   source.surcharges(), exercice.chaine if exercice else None)
    return chaine


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
        v = self._depot.verrouiller(copie_id)
        if etape == Etape.IA:
            return bool(v.etat.etape) and v.copie.statut not in TERMINEES
        return v.etat.etape == etape.value

    def executer(self, copie_id: str, terminee: Etape | None = None) -> None:
        """Passe à l'étape active suivante ; un signal d'une étape qui n'est plus la courante est ignoré."""
        v = self._depot.verrouiller(copie_id)  # un second signal concurrent lit l'étape déjà avancée
        copie, etat = v.copie, v.etat
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
        if etape == Etape.JURY and not self._depot.jures(copie.id):  # personne à attendre
            self._journal(copie.id, SYSTEME, "jury sauté", {}, {"cohorte": copie.cohorte})
            self._entrer(copie, quittee, etape_suivante(chaine, etape), chaine)
            return
        statut = _statut(copie.statut, quittee, etape)
        if statut != copie.statut:
            copie = copie.passer_a(statut)
        delai, maintenant = chaine.config(etape).delai_heures, self._horloge()
        echeance = maintenant + timedelta(hours=delai)
        if etape == Etape.PAIRS:  # au-delà du butoir, plus aucune relecture n'est attendue : la copie avance
            butoir = maintenant + timedelta(days=chaine.pairs_attente_max_jours)
            echeance = min(echeance, butoir)
            self._depot.fixer_butoir(copie.id, butoir)
        self._depot.changer_statut(copie.id, copie.statut, etape.value, echeance)
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
        for copie_id in self._depot.copies_en_souffrance():
            self._isoler(lambda copie_id=copie_id: self._souffrance(copie_id, maintenant))

    # --- relecture échue : rappel, puis réattribuée ou annulée, le relecteur en retard étant dispensé ---
    def _relecture(self, r: Relecture, maintenant: datetime) -> None:
        """Ni le rappel ni la réattribution ne dépassent le butoir de la copie."""
        v = self._depot.verrouiller(r.copie)  # copie puis relecture : ordre unique des verrous
        copie, butoir = v.copie, v.etat.butoir or maintenant  # sans butoir enregistré : aucune prolongation
        r = self._relectures.verrouiller_relecture(r.id)
        if r.statut != StatutRelecture.A_FAIRE or r.echeance is None or r.echeance > maintenant:
            return  # relue ou déjà traitée entre-temps
        chaine = self._avancer.chaine(copie)
        config = chaine.config(Etape.PAIRS)
        prolongee = maintenant + timedelta(hours=config.delai_heures)
        if not r.rappelee and butoir > maintenant:
            echeance = min(prolongee, butoir)
            self._relectures.rappeler(r.id, echeance)
            self._notifier(r.relecteur, f"Rappel : une relecture vous attend, à rendre avant le "
                                        f"{echeance:%d/%m/%Y à %H:%M}. Passé ce délai, elle sera retirée.")
            self._journal(copie.id, SYSTEME, "rappel de relecture", {"echeance": r.echeance},
                          {"echeance": echeance})
            return
        nouveau = None
        reattribuees = sum(x.statut == StatutRelecture.REATTRIBUEE for x in self._relectures.relectures_copie(copie.id))
        if (config.expiration == Expiration.REATTRIBUER and prolongee <= butoir
                and reattribuees < chaine.pairs_reattributions_max):
            rendues = self._relectures.copies_rendues(copie.exercice, copie.cohorte)
            nouveau = AttribuerPairs(self._relectures, self._horloge).reattribuer(copie, rendues, config.delai_heures)
        if nouveau:
            self._relectures.changer_statut_relecture(r.id, StatutRelecture.REATTRIBUEE)
            self._journal(copie.id, SYSTEME, "relecture réattribuée", {"relecteur": r.relecteur},
                          {"relecteur": nouveau})
        else:
            self._relectures.changer_statut_relecture(r.id, StatutRelecture.ANNULEE)
            self._journal(copie.id, SYSTEME, "relecture annulée", {"relecteur": r.relecteur}, {})
        self._dispenser(copie, r)

    def _dispenser(self, copie: Copie, r: Relecture) -> None:
        """Le relecteur en retard perd sa relecture : sa propre note n'est plus masquée faute de relectures."""
        for sienne in self._relectures.copies_rendues(copie.exercice, copie.cohorte):
            if sienne.apprenant == r.relecteur:
                self._relectures.dispenser(sienne.id)
                self._journal(sienne.id, SYSTEME, "relectures dispensées", {}, {"relecture": r.id})

    # --- étape échue -------------------------------------------------------------------------------
    def _copie(self, copie_id: str, maintenant: datetime) -> None:
        """L'échéance enregistrée à l'entrée dans l'étape fait foi ; l'action est celle réglée pour l'étape."""
        v = self._depot.verrouiller(copie_id)
        copie, etat = v.copie, v.etat
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
        if etape == Etape.PAIRS:
            if self._attendre_relectures(copie, etat, maintenant):
                return
            if action == Expiration.REATTRIBUER:
                libelle = Expiration.PASSER.value  # personne d'autre : la copie avance avec les relectures obtenues
        self._journal(copie_id, SYSTEME, libelle, {"etape": etape.value}, {})
        if etape == Etape.PAIRS:
            self._clore_pairs(copie, chaine)
        self._avancer.executer(copie_id, etape)

    def _clore_pairs(self, copie: Copie, chaine: Chaine) -> None:
        """La copie avance avec les relectures obtenues ; sous le minimum réglé, leur médiane ne compte pas."""
        faites = sum(r.statut == StatutRelecture.FAITE for r in self._relectures.relectures_copie(copie.id))
        minimum = chaine.pairs_minimum_releves
        issue = "relectures obtenues" if faites >= minimum else "relectures insuffisantes"
        self._journal(copie.id, SYSTEME, f"pairs clos : {issue}", {}, {"faites": faites, "minimum": minimum})

    def _attendre_relectures(self, copie: Copie, etat: Etat, maintenant: datetime) -> bool:
        """Quelle que soit l'action réglée, une relecture rappelée ou réattribuée encore dans son délai est
        attendue, jamais au-delà du butoir réglé dans la console ; passé ce butoir, ou pour une relecture restée
        en retard, la relecture est retirée et son relecteur dispensé."""
        en_cours = [r for r in self._relectures.relectures_copie(copie.id) if r.statut == StatutRelecture.A_FAIRE]
        attente = [r.echeance for r in en_cours if r.echeance and r.echeance > maintenant]
        if attente and etat.butoir and etat.butoir > maintenant:
            echeance = min(max(attente), etat.butoir)
            self._depot.changer_statut(copie.id, copie.statut, Etape.PAIRS.value, echeance)
            self._journal(copie.id, SYSTEME, "attente des relectures", {"echeance": etat.echeance},
                          {"echeance": echeance})
            return True
        for r in en_cours:
            self._relectures.changer_statut_relecture(r.id, StatutRelecture.ANNULEE)
            self._journal(copie.id, SYSTEME, "relecture annulée", {"relecteur": r.relecteur}, {})
            self._dispenser(copie, r)
        return False

    def _formateur(self, copie: Copie, etat: Etat, action: Expiration, delai: int, maintenant: datetime) -> None:
        """Formateur échu : les suppléants dans l'ordre, puis le responsable pédagogique, chacun prévenu ; l'escalade
        épuisée, la copie est en souffrance (rappels quotidiens, puis l'action réglée dans la console)."""
        reglages = self._source.reglages()
        if action == Expiration.PUBLIER_PROVISOIRE and reglages.publication_provisoire:
            self._provisoire(copie)
            return
        equipe = self._depot.equipe(copie.id)
        responsable = equipe.responsable or reglages.responsable_pedagogique
        suivant = prochain_recours(etat.escalade_a, equipe.suppleants, responsable)
        avant = [etat.escalade_a] if etat.escalade_a else sorted(self._depot.titulaires(copie.id))
        lien = LIEN_CORRECTEUR.format(copie.id)
        if suivant:
            self._depot.escalader(copie.id, suivant, maintenant + timedelta(hours=delai))
            self._journal(copie.id, SYSTEME, "escalader", {"correcteurs": avant}, {"correcteurs": [suivant]})
            self._notifier(suivant, f"Une copie vous est confiée (formateur en retard) : {lien}")
            return
        # plus d'échéance : prévenus une seule fois, la copie attend qu'un humain publie
        self._depot.changer_statut(copie.id, copie.statut, Etape.FORMATEUR.value, None)
        self._depot.marquer_souffrance(copie.id, maintenant)
        self._journal(copie.id, SYSTEME, "escalade épuisée", {"correcteurs": avant}, {"correcteurs": avant})
        for destinataire in sorted((self._depot.titulaires(copie.id) | set(avant) | {responsable}) - {""}):
            self._notifier(destinataire, f"Copie en attente de correction, sans autre recours : {lien}")

    def _souffrance(self, copie_id: str, maintenant: datetime) -> None:
        """Copie en souffrance : levée une fois sortie de la chaîne ; sinon, passé le délai réglé, l'action réglée
        (publication provisoire si elle est permise) ; sinon, au plus un rappel par jour au responsable."""
        v = self._depot.verrouiller(copie_id)
        copie, etat = v.copie, v.etat
        if etat.souffrance_depuis is None:
            return
        if copie.statut in TERMINEES:
            self._depot.lever_souffrance(copie_id)
            return
        reglages = self._source.reglages()
        reste = reste_avant_action_souffrance(reglages, etat.souffrance_depuis, maintenant)
        if reste is not None and not reste:
            self._journal(copie_id, SYSTEME, "souffrance : publication provisoire",
                          {"depuis": etat.souffrance_depuis}, {})
            self._provisoire(copie)
            self._depot.lever_souffrance(copie_id)
            return
        if etat.rappel_souffrance and maintenant - etat.rappel_souffrance < timedelta(days=1):
            return
        responsable = self._depot.equipe(copie_id).responsable or reglages.responsable_pedagogique
        if responsable:
            depuis = f"{etat.souffrance_depuis:%d/%m/%Y à %H:%M}"
            self._notifier(responsable, f"Rappel : copie en souffrance depuis le {depuis}, aucun correcteur ne l'a "
                                        f"prise : {LIEN_CORRECTEUR.format(copie_id)}")
            self._journal(copie_id, SYSTEME, "rappel : copie en souffrance", {}, {"destinataire": responsable})
        self._depot.rappeler_souffrance(copie_id, maintenant)

    def _provisoire(self, copie: Copie) -> None:
        self._depot.changer_statut(copie.id, copie.passer_a(Statut.PROVISOIRE).statut, Etape.FORMATEUR.value, None)
        self._journal(copie.id, SYSTEME, "publication provisoire", {"statut": copie.statut.value},
                      {"statut": Statut.PROVISOIRE.value})
        lien = LIEN_RETOUR.format(copie.id)
        self._notifier(copie.apprenant, f"Votre exercice {copie.exercice} a une note provisoire, en attente de "
                                        f"validation par le formateur. Retour détaillé : {lien}")
