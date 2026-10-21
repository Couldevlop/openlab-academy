"""Cas d'usage : correction humaine d'une copie (formateur, jury), validation par lots, publication, délégations.

Seul un humain publie une note : un titulaire de la copie (formateur de la cohorte ou destinataire de l'escalade),
son délégataire, ou le super administrateur ; jamais l'auteur de la copie. L'accès est vérifié avant toute lecture
du contenu ou de l'état de la copie. Chaque note proposée ou publiée est journalisée avec l'acteur et, s'il agit
par délégation, le titulaire au nom duquel il agit.

Gating des notes (Coursera) : tant que l'apprenant doit des relectures, la publication n'écrit dans LMS qu'un
lien, sans note ni réussite ; le statut LMS et le résumé sont différés, puis libérés quand le gating tombe
(relectures faites, dispense ou relectures retirées).
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from statistics import fmean
from typing import Protocol

from openlab_academy.application.pairs import DepotRelectures, Relecture, StatutRelecture
from openlab_academy.application.pre_corriger import SIGNALEMENT
from openlab_academy.application.soumettre_copie import Contenu
from openlab_academy.domain.copie import (
    Copie, CopieVerrouillee, Etat, Proposition, Source, Statut, ecarts, lots, mediane)
from openlab_academy.domain.delegation import Delegation, FaitsDelegation, peut_corriger, verifier_delegation
from openlab_academy.domain.grille import Grille, GrilleInvalide
from openlab_academy.domain.reglages_evaluation import Chaine, Etape

COMMENTAIRE_MAX = 5000
GENERAL = "general"  # commentaire d'ensemble, à côté des commentaires par critère
CORRIGEABLES = (Statut.A_CORRIGER, Statut.PROVISOIRE)
REMPLACEE = "version remplacée par un nouveau rendu : seule la dernière version se corrige"
LIEN_RETOUR = "/espace/retour/{}"
SYSTEME = "systeme"


class AccesRefuse(Exception):
    """L'acteur n'a pas le droit d'agir sur cette ressource (contrôle d'accès côté serveur)."""


class CorrectionRefusee(ValueError):
    """La correction demandée est invalide ou arrive au mauvais moment."""


class DepotCorrection(Protocol):
    def copie(self, copie_id: str) -> Copie: ...
    def cours(self, exercice: str) -> str | None: ...  # cours de l'exercice : périmètre des délégations
    def etat(self, copie_id: str) -> Etat: ...
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...
    def grille(self, copie_id: str) -> Grille: ...
    def propositions(self, copie_id: str, verrouillee: bool = False) -> list[Proposition]:
        """Verrouillée : lecture à jour (après le verrou de la copie), pas l'instantané de la transaction."""
    def ajouter_proposition(self, copie_id: str, p: Proposition) -> None: ...
    def changer_statut(self, copie_id: str, statut: Statut, etape: str, echeance: datetime | None) -> None: ...
    def titulaires(self, copie_id: str) -> set[str]: ...
    def jures(self, copie_id: str) -> set[str]: ...
    def dispensee(self, copie_id: str) -> bool: ...
    def courante(self, copie_id: str) -> bool:
        """Lecture verrouillante : la copie est-elle toujours la dernière version de sa soumission ?"""
    def publier(self, copie_id: str, note: float, note_sur: int, reussite: bool, resume: str, lien: str,
                differe: bool) -> None:
        """Différé : lien seul dans LMS, statut LMS inchangé."""


class DepotLiberation(Protocol):
    def verrouiller(self, copie_id: str) -> CopieVerrouillee: ...
    def courante(self, copie_id: str) -> bool: ...
    def dispensee(self, copie_id: str) -> bool: ...
    def resultat(self, copie_id: str) -> tuple[float, int, bool]: ...
    def copies_differees(self, apprenant: str | None = None) -> list[str]: ...
    def differee(self, copie_id: str) -> bool: ...
    def liberer(self, copie_id: str, reussite: bool, resume: str, lien: str) -> None: ...


class DepotConsultation(DepotCorrection, Protocol):
    def copies_en_correction(self, exercice: str | None = None,
                             pour: frozenset[str] | None = None) -> list[str]: ...  # pour : None = toutes
    def contenu(self, copie_id: str) -> Contenu: ...
    def texte_lisible(self, copie_id: str) -> str: ...
    def consigne(self, exercice: str) -> str: ...
    def titre(self, exercice: str) -> str: ...
    def signalee(self, copie_id: str) -> bool: ...
    def versions(self, copie_id: str) -> list[dict]: ...  # versions antérieures : copie, version, rendue_le


class DepotDelegations(Protocol):
    """Création et révocation passent par l'adaptateur, qui consigne et prévient titulaire et délégataire."""

    def creer_delegation(self, d: Delegation) -> str: ...
    def delegation(self, delegation_id: str) -> Delegation | None: ...
    def revoquer_delegation(self, delegation_id: str) -> None: ...


class Avanceur(Protocol):
    def chaine(self, copie: Copie) -> Chaine: ...
    def executer(self, copie_id: str, terminee: Etape | None = None) -> None: ...


Journal = Callable[[str, str, str, dict, dict, str | None], None]


# --- règles de saisie --------------------------------------------------------------------------------------
def _entier(valeur) -> bool:
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def valider_niveaux(grille: Grille, niveaux) -> dict[str, int]:
    """Un niveau existant pour chaque critère de la grille, rien d'autre."""
    if not isinstance(niveaux, dict) or set(niveaux) != {c.code for c in grille.criteres}:
        raise CorrectionRefusee("un niveau est attendu pour chaque critère de la grille")
    if not all(_entier(n) for n in niveaux.values()):
        raise CorrectionRefusee("niveau invalide : un entier est attendu")
    try:
        grille.note(niveaux, 1)
    except GrilleInvalide as e:
        raise CorrectionRefusee(f"niveau invalide : {e}") from None
    return dict(niveaux)


def nettoyer_commentaires(grille: Grille, commentaires) -> dict[str, str]:
    """Commentaires en texte brut, par critère connu (ou d'ensemble), bornés en longueur ; les vides sont omis."""
    if commentaires is None:
        return {}
    if not isinstance(commentaires, dict):
        raise CorrectionRefusee("commentaires : un dictionnaire par critère est attendu")
    if set(commentaires) - {c.code for c in grille.criteres} - {GENERAL}:
        raise CorrectionRefusee("commentaire sur un critère inconnu")
    if not all(isinstance(t, str) for t in commentaires.values()):
        raise CorrectionRefusee("commentaire invalide : du texte est attendu")
    nets = {c: t.strip() for c, t in commentaires.items()}
    if any(len(t) > COMMENTAIRE_MAX for t in nets.values()):
        raise CorrectionRefusee(f"commentaire trop long ({COMMENTAIRE_MAX} caractères au plus)")
    return {c: t for c, t in nets.items() if t}


def resume_note(note: float, note_sur: int, reussite: bool) -> str:
    return f"Note : {note:g}/{note_sur} ({'réussi' if reussite else 'non validé'})."


def note_masquee(chaine: Chaine, copie: Copie, dispensee: bool, relectures: Iterable[Relecture]) -> bool:
    """Gating : la note de l'auteur reste masquée tant qu'il doit une relecture, sauf dispense."""
    return (chaine.note_masquee_avant_relectures and not dispensee
            and any(r.relecteur == copie.apprenant and r.statut == StatutRelecture.A_FAIRE for r in relectures))


# --- synthèse des propositions ------------------------------------------------------------------------------
def derniere(props: Iterable[Proposition], source: Source) -> Proposition | None:
    return next((p for p in reversed(list(props)) if p.source == source), None)


def par_auteur(props: Iterable[Proposition], source: Source) -> tuple[Proposition, ...]:
    """Dernière proposition de chaque auteur (le titulaire, pour une proposition faite par délégation)."""
    retenues: dict[str, Proposition] = {}
    for p in props:
        if p.source == source:
            retenues[p.au_nom_de or p.auteur] = p
    return tuple(retenues.values())


@dataclass(frozen=True)
class Synthese:
    """Ce que le correcteur voit d'une copie : chaque source, médianes des pairs et du jury, écarts."""

    auto_evaluation: Proposition | None
    controles: tuple[str, ...]
    ia: Proposition | None
    pairs: tuple[Proposition, ...]
    jury: tuple[Proposition, ...]
    formateur: Proposition | None
    mediane_pairs: dict[str, int] = field(init=False)
    mediane_jury: dict[str, int] = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "mediane_pairs", mediane(list(self.pairs)))
        object.__setattr__(self, "mediane_jury", mediane(list(self.jury)))

    @property
    def ecarts(self) -> set[str]:
        """Critères où IA, médiane des pairs et formateur divergent de plus d'un niveau."""
        sources = [p for p in (self.ia, self.formateur) if p is not None]
        if self.pairs:
            sources.append(Proposition(Source.PAIR, "", self.mediane_pairs))
        return ecarts(sources)

    @property
    def ecarts_ia_pairs(self) -> set[str]:
        """Écart de plus d'un niveau entre l'IA et la médiane des pairs : la copie sort des lots."""
        if self.ia is None or not self.pairs:
            return set()
        return ecarts([self.ia, Proposition(Source.PAIR, "", self.mediane_pairs)])

    def note_provisoire(self, grille: Grille, note_sur: int) -> float | None:
        try:
            return grille.note(self.niveaux_provisoires() or {}, note_sur)
        except GrilleInvalide:  # rien d'humain à noter encore
            return None

    def niveaux_provisoires(self) -> dict[str, int] | None:
        """Note provisoire : formateur, sinon jury, sinon pairs. Jamais la seule IA (non montrée à l'apprenant)."""
        if self.formateur is not None:
            return self.formateur.niveaux
        return self.mediane_jury or self.mediane_pairs or None


def synthese(props: list[Proposition]) -> Synthese:
    controles = derniere(props, Source.CONTROLES)
    return Synthese(derniere(props, Source.AUTO_EVALUATION),
                    tuple(controles.commentaires.values()) if controles else (), derniere(props, Source.IA),
                    par_auteur(props, Source.PAIR), par_auteur(props, Source.JURY), derniere(props, Source.FORMATEUR))


def fiabilite(copies: Iterable[list[Proposition]]) -> dict[str, float]:
    """Écart moyen, en niveaux, entre la proposition IA et la correction du formateur, par critère."""
    ecarts_: dict[str, list[int]] = {}
    for props in copies:
        ia, formateur = derniere(props, Source.IA), derniere(props, Source.FORMATEUR)
        if ia is None or formateur is None:
            continue
        for critere in sorted(set(ia.niveaux) & set(formateur.niveaux)):
            ecarts_.setdefault(critere, []).append(abs(ia.niveaux[critere] - formateur.niveaux[critere]))
    return {c: round(fmean(v), 2) for c, v in ecarts_.items()}


# --- contrôle d'accès --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Habilitation:
    source: Source  # FORMATEUR ou JURY
    au_nom_de: str | None = None  # titulaire représenté, en cas de délégation


class Acces:
    def __init__(self, depot: DepotCorrection, delegations: Callable[[], Iterable[Delegation]],
                 horloge: Callable[[], datetime], administrateur: Callable[[str], bool]):
        self._depot = depot
        self._delegations = delegations
        self._horloge = horloge
        self._administrateur = administrateur

    def administrateur(self, acteur: str) -> bool:
        return self._administrateur(acteur)

    def mandants(self, acteur: str) -> frozenset[str]:
        """Titulaires qui délèguent actuellement à l'acteur (quel que soit le périmètre)."""
        maintenant = self._horloge()
        return frozenset(d.titulaire for d in self._delegations()
                         if d.delegataire == acteur and not d.revoquee and d.fin is not None
                         and d.debut <= maintenant <= d.fin)

    def _mandant(self, acteur: str, copie: Copie, titulaires: set[str]) -> str | None:
        """Titulaire de la délégation active la plus spécifique dont l'acteur est délégataire."""
        maintenant = self._horloge()
        cours = self._depot.cours(copie.exercice)
        actives = [d for d in self._delegations() if d.delegataire == acteur and d.titulaire in titulaires
                   and d.couvre(maintenant, copie.cohorte, copie.exercice, cours)]
        return max(actives, key=lambda d: d.specificite).titulaire if actives else None

    def correcteur(self, acteur: str, copie: Copie, etat: Etat) -> Habilitation:
        """Titulaires, destinataire de l'escalade, leurs délégataires, super administrateur ; jamais l'auteur."""
        if acteur == copie.apprenant:
            raise AccesRefuse("on ne corrige pas sa propre copie")
        titulaires = self._depot.titulaires(copie.id) | ({etat.escalade_a} if etat.escalade_a else set())
        if acteur in titulaires or self._administrateur(acteur):
            return Habilitation(Source.FORMATEUR)
        if peut_corriger(acteur, copie, titulaires, tuple(self._delegations()), self._horloge(),
                         self._depot.cours(copie.exercice)):
            return Habilitation(Source.FORMATEUR, self._mandant(acteur, copie, titulaires))
        raise AccesRefuse("ni titulaire ni délégataire de cette copie")

    def habilitation(self, acteur: str, copie: Copie, etat: Etat) -> Habilitation:
        """À l'étape du jury, un juré (ou son délégataire) note comme juré ; sinon il faut être correcteur."""
        if etat.etape == Etape.JURY.value and acteur != copie.apprenant:
            jures = self._depot.jures(copie.id)
            if acteur in jures:
                return Habilitation(Source.JURY)
            mandant = self._mandant(acteur, copie, jures)
            if mandant:
                return Habilitation(Source.JURY, mandant)
        return self.correcteur(acteur, copie, etat)


def _corrigeable(copie: Copie) -> None:
    if copie.statut == Statut.REMPLACEE:
        raise CorrectionRefusee(REMPLACEE)
    if copie.statut not in CORRIGEABLES:
        raise CorrectionRefusee(f"la copie n'est pas à corriger (statut : {copie.statut.value})")


# --- cas d'usage d'écriture --------------------------------------------------------------------------------
class CorrigerCopie:
    def __init__(self, depot: DepotCorrection, acces: Acces, avanceur: Avanceur, journal: Journal):
        self._depot = depot
        self._acces = acces
        self._avanceur = avanceur
        self._journal = journal

    def executer(self, acteur: str, copie_id: str, niveaux, commentaires=None) -> None:
        v = self._depot.verrouiller(copie_id)
        hab = self._acces.habilitation(acteur, v.copie, v.etat)
        _corrigeable(v.copie)
        grille = self._depot.grille(copie_id)
        niveaux = valider_niveaux(grille, niveaux)
        nets = nettoyer_commentaires(grille, commentaires)
        props = self._depot.propositions(copie_id, verrouillee=True)  # vote d'un autre juré validé entre-temps
        precedente = next((p for p in reversed(props) if p.source == hab.source
                           and (p.au_nom_de or p.auteur) == (hab.au_nom_de or acteur)), None)
        self._depot.ajouter_proposition(copie_id, Proposition(hab.source, acteur, niveaux, nets,
                                                              au_nom_de=hab.au_nom_de))
        action = "note du jury" if hab.source == Source.JURY else "correction"
        self._journal(copie_id, acteur, action, {"niveaux": precedente.niveaux if precedente else {}},
                      {"niveaux": niveaux}, hab.au_nom_de)
        if hab.source == Source.JURY:
            votants = {p.au_nom_de or p.auteur for p in par_auteur(props, Source.JURY)} | {hab.au_nom_de or acteur}
            if self._depot.jures(copie_id) <= votants:  # tous les jurés ont noté : la copie avance
                self._avanceur.executer(copie_id, Etape.JURY)


class ValiderLot:
    """Le formateur valide d'un geste la proposition IA de chaque copie d'un lot ; tout ou rien."""

    def __init__(self, depot: DepotCorrection, acces: Acces, seuil_confiance: float, journal: Journal):
        self._depot = depot
        self._acces = acces
        self._seuil = seuil_confiance
        self._journal = journal

    def executer(self, acteur: str, copie_ids: list[str]) -> list[str]:
        if not copie_ids:
            raise CorrectionRefusee("aucune copie à valider")
        retenues = []
        for copie_id in sorted(set(copie_ids)):  # ordre de verrouillage stable
            v = self._depot.verrouiller(copie_id)
            hab = self._acces.correcteur(acteur, v.copie, v.etat)
            _corrigeable(v.copie)
            s = synthese(self._depot.propositions(copie_id, verrouillee=True))  # correction d'un délégataire
            ia = s.ia
            if ia is None or ia.confiance is None or ia.confiance < self._seuil:
                raise CorrectionRefusee(f"copie {copie_id} hors lot : proposition IA absente ou peu sûre")
            if s.ecarts_ia_pairs:
                raise CorrectionRefusee(f"copie {copie_id} hors lot : écart entre l'IA et les pairs")
            if s.formateur is not None:  # une correction humaine n'est jamais écrasée par un lot
                raise CorrectionRefusee(f"copie {copie_id} hors lot : déjà corrigée, à traiter une par une")
            niveaux = valider_niveaux(self._depot.grille(copie_id), ia.niveaux)
            retenues.append((copie_id, hab, niveaux, ia))
        for copie_id, hab, niveaux, ia in retenues:  # écritures après toutes les vérifications
            self._depot.ajouter_proposition(copie_id, Proposition(Source.FORMATEUR, acteur, niveaux,
                                                                  dict(ia.commentaires), au_nom_de=hab.au_nom_de))
            self._journal(copie_id, acteur, "validation par lot", {"niveaux": {}}, {"niveaux": niveaux},
                          hab.au_nom_de)
        return [r[0] for r in retenues]


class PublierNote:
    """Cas d'usage unique de publication : note sur N, statut publié, soumission LMS réussie ou non.

    Si le gating masque encore la note de l'apprenant, ni la note ni la réussite ne sortent : LMS ne reçoit
    qu'un lien et son statut est différé jusqu'à la libération (`LibererNote`)."""

    def __init__(self, depot: DepotCorrection, relectures: DepotRelectures, acces: Acces, avanceur: Avanceur,
                 journal: Journal, notifier: Callable[[str, str], None] = lambda *_: None):
        self._depot = depot
        self._relectures = relectures
        self._acces = acces
        self._avanceur = avanceur
        self._journal = journal
        self._notifier = notifier

    def executer(self, acteur: str, copie_id: str) -> float:
        v = self._depot.verrouiller(copie_id)
        copie = v.copie
        hab = self._acces.correcteur(acteur, copie, v.etat)
        _corrigeable(copie)
        if not self._depot.courante(copie_id):  # avant toute écriture dans LMS : un rendu a pu la remplacer
            raise CorrectionRefusee(REMPLACEE)
        s = synthese(self._depot.propositions(copie_id, verrouillee=True))
        if s.formateur is None:
            raise CorrectionRefusee("aucune correction du formateur à publier")
        chaine = self._avanceur.chaine(copie)
        grille = self._depot.grille(copie_id)
        note = grille.note(s.formateur.niveaux, chaine.note_sur)
        reussite = note >= chaine.seuil_reussite
        avant = {"statut": copie.statut.value}
        if copie.statut == Statut.PROVISOIRE:
            avant["note"] = s.note_provisoire(grille, chaine.note_sur)
        differe = note_masquee(chaine, copie, self._depot.dispensee(copie_id),
                               self._relectures.relectures(copie.exercice, copie.cohorte, verrouillee=True))
        self._depot.changer_statut(copie_id, copie.passer_a(Statut.PUBLIEE).statut, "", None)
        lien = LIEN_RETOUR.format(copie_id)
        resume = "" if differe else resume_note(note, chaine.note_sur, reussite)
        self._depot.publier(copie_id, note, chaine.note_sur, reussite, resume, lien, differe)
        self._journal(copie_id, acteur, "note publiée", avant,
                      {"statut": Statut.PUBLIEE.value, "note": note, "reussite": reussite, "lms_differe": differe},
                      hab.au_nom_de)
        if differe:
            self._notifier(copie.apprenant, f"Votre exercice {copie.exercice} est corrigé. Terminez vos relectures "
                                            f"pour découvrir votre note. Retour détaillé : {lien}")
        else:
            self._notifier(copie.apprenant, f"Votre exercice {copie.exercice} est corrigé. {resume} "
                                            f"Retour détaillé : {lien}")
        return note


class LibererNote:
    """Le gating est tombé (relectures faites, dispense, relectures retirées) : statut LMS et résumé sont écrits,
    l'apprenant est prévenu. Rien ne se passe tant qu'une relecture est encore due."""

    def __init__(self, depot: DepotLiberation, relectures: DepotRelectures, chaine: Callable[[Copie], Chaine],
                 journal: Journal, notifier: Callable[[str, str], None] = lambda *_: None):
        self._depot = depot
        self._relectures = relectures
        self._chaine = chaine
        self._journal = journal
        self._notifier = notifier

    def executer(self, copie_id: str) -> bool:
        copie = self._depot.verrouiller(copie_id).copie
        if not self._depot.differee(copie_id):
            return False  # déjà libérée
        if copie.statut == Statut.REMPLACEE or not self._depot.courante(copie_id):
            raise CorrectionRefusee(REMPLACEE)
        if note_masquee(self._chaine(copie), copie, self._depot.dispensee(copie_id),
                        self._relectures.relectures(copie.exercice, copie.cohorte)):
            return False
        note, note_sur, reussite = self._depot.resultat(copie_id)
        lien, resume = LIEN_RETOUR.format(copie_id), resume_note(note, note_sur, reussite)
        self._depot.liberer(copie_id, reussite, resume, lien)
        self._journal(copie_id, SYSTEME, "note libérée", {"lms_differe": True}, {"lms_differe": False}, None)
        self._notifier(copie.apprenant, f"Votre note de l'exercice {copie.exercice} est disponible. {resume} "
                                        f"Retour détaillé : {lien}")
        return True


# --- vues du correcteur ------------------------------------------------------------------------------------
def _ia(p: Proposition | None) -> dict | None:
    if p is None:
        return None
    return {"niveaux": p.niveaux, "justifications": p.commentaires, "citations": p.citations, "confiance": p.confiance}


class ConsulterCorrection:
    def __init__(self, depot: DepotConsultation, acces: Acces, seuil_confiance: Callable[[], float],
                 chaine: Callable[[Copie], Chaine]):
        self._depot = depot
        self._acces = acces
        self._seuil = seuil_confiance
        self._chaine = chaine

    def _habilitation(self, acteur: str, copie_id: str) -> tuple[Copie, Etat, Habilitation] | None:
        copie, etat = self._depot.copie(copie_id), self._depot.etat(copie_id)
        try:
            return copie, etat, self._acces.habilitation(acteur, copie, etat)
        except AccesRefuse:
            return None

    def file(self, acteur: str, exercice: str | None = None) -> dict:
        """Copies que l'acteur peut corriger ou noter comme juré, et lots de copies validables d'un geste."""
        copies, candidates = [], {}
        pour = None if self._acces.administrateur(acteur) else frozenset({acteur}) | self._acces.mandants(acteur)
        for copie_id in self._depot.copies_en_correction(exercice, pour):
            trouve = self._habilitation(acteur, copie_id)
            if trouve is None:
                continue
            copie, etat, hab = trouve
            s = synthese(self._depot.propositions(copie_id))
            copies.append({"copie": copie_id, "apprenant": copie.apprenant, "exercice": copie.exercice,
                           "cohorte": copie.cohorte, "version": copie.version, "statut": copie.statut.value,
                           "etape": etat.etape, "echeance": etat.echeance, "role": hab.source.value,
                           "confiance": s.ia.confiance if s.ia else None, "ecarts": sorted(s.ecarts),
                           "signalee": self._depot.signalee(copie_id), "corrigee": s.formateur is not None})
            if (hab.source == Source.FORMATEUR and s.ia is not None and s.formateur is None
                    and not s.ecarts_ia_pairs):
                candidates.setdefault(copie.exercice, {})[copie_id] = s.ia
        seuil = self._seuil() if candidates else 0.0  # réglages lus seulement s'il y a des lots possibles
        groupes = [lot for par_exercice in candidates.values() for lot in lots(par_exercice, seuil)]
        return {"copies": copies, "lots": groupes}

    def copie(self, acteur: str, copie_id: str) -> dict:
        trouve = self._habilitation(acteur, copie_id)
        if trouve is None:
            raise AccesRefuse("copie hors de votre correction")
        copie, etat, hab = trouve
        s = synthese(self._depot.propositions(copie_id))
        contenu = self._depot.contenu(copie_id)
        formateur = s.formateur
        chaine = self._chaine(copie)
        return {
            "copie": copie_id, "apprenant": copie.apprenant, "exercice": copie.exercice, "cohorte": copie.cohorte,
            "titre": self._depot.titre(copie.exercice), "note_sur": chaine.note_sur,
            "seuil_reussite": chaine.seuil_reussite,
            "version": copie.version, "statut": copie.statut.value, "etape": etat.etape, "echeance": etat.echeance,
            "role": hab.source.value, "au_nom_de": hab.au_nom_de,
            "contenu": self._depot.texte_lisible(copie_id), "source_url": contenu.source_url,
            "commit": contenu.commit, "consigne": self._depot.consigne(copie.exercice),
            "grille": self._depot.grille(copie_id).vers_dict(),
            "auto_evaluation": s.auto_evaluation.niveaux if s.auto_evaluation else None,
            "controles": list(s.controles), "ia": _ia(s.ia),
            "pairs": {"mediane": s.mediane_pairs, "nombre": len(s.pairs),
                      "commentaires": [p.commentaires for p in s.pairs]},
            "jury": {"mediane": s.mediane_jury, "nombre": len(s.jury), "attendus": len(self._depot.jures(copie_id))},
            "formateur": None if formateur is None else {
                "niveaux": formateur.niveaux, "commentaires": formateur.commentaires, "auteur": formateur.auteur,
                "au_nom_de": formateur.au_nom_de},
            "ecarts": sorted(s.ecarts), "signalement": SIGNALEMENT if self._depot.signalee(copie_id) else "",
            "remplacee": copie.statut == Statut.REMPLACEE, "versions_precedentes": self._depot.versions(copie_id),
        }


# --- délégations -------------------------------------------------------------------------------------------
class GererDelegations:
    """On ne délègue que ses propres corrections ; un superviseur (super administrateur, responsable
    pédagogique) délègue pour le compte de n'importe quel correcteur."""

    def __init__(self, depot: DepotDelegations, faits: Callable[[Delegation], FaitsDelegation],
                 superviseur: Callable[[str], bool], horloge: Callable[[], datetime]):
        self._depot = depot
        self._faits = faits
        self._superviseur = superviseur
        self._horloge = horloge

    def deleguer(self, acteur: str, d: Delegation) -> str:
        """Refus d'autorisation : AccesRefuse ; règle commune enfreinte : DelegationRefusee."""
        if d.titulaire != acteur and not self._superviseur(acteur):
            raise AccesRefuse("vous ne pouvez déléguer que vos propres corrections")
        verifier_delegation(d, self._faits(d), self._horloge(), creation=True)
        return self._depot.creer_delegation(d)

    def revoquer(self, acteur: str, delegation_id: str) -> None:
        d = self._depot.delegation(delegation_id)
        if d is None or (d.titulaire != acteur and not self._superviseur(acteur)):
            raise AccesRefuse("délégation introuvable ou hors de votre compte")
        if not d.revoquee:  # toujours possible, même si les habilitations ont changé depuis
            self._depot.revoquer_delegation(delegation_id)
