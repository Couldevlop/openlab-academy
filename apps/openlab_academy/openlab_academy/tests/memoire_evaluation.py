"""Dépôts en mémoire de la chaîne de correction : copies, état d'étape, relectures, réglages."""
from dataclasses import replace
from datetime import datetime, timedelta

from openlab_academy.application.pairs import Relecture, StatutRelecture
from openlab_academy.application.soumettre_copie import Contenu, Exercice
from openlab_academy.domain.equipe import EquipeEffective
from openlab_academy.domain.copie import Copie, CopieVerrouillee, Etat, Source, Statut, etape_suivante
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
        self.suppleants_: tuple[str, ...] = ()
        self.responsable_ = ""
        self.cours_: dict[str, str] = {}
        self.verrous: list[str] = []
        self.verrou_tenu = False
        self.reservations_ia: dict = {}
        self.evenements: list = []
        self.paires_concurrentes: set[tuple[str, str]] = set()  # insérées par une autre transaction
        self.contenus: dict[str, Contenu] = {}
        self.consignes = {"EX1": "Analysez le cas."}
        self.titres = {"EX1": "Mise en situation 01"}
        self.jures_: set[str] = set()
        self.resultats: dict[str, tuple] = {}
        self.publications: list[tuple] = []
        self.signalees: set[str] = set()
        self.auto_evals: dict[tuple[str, str], dict] = {}
        self.inscrits: set[tuple[str, str]] = set()
        self.delegations_: dict[str, object] = {}
        self.differees_: set[str] = set()
        self.liberations: list[tuple] = []
        self.filtres_correction: list = []
        self.lectures_verrouillees: list[tuple[str, str]] = []
        self.non_courantes: set[str] = set()  # remplacées par un rendu d'une autre transaction
        self.rendues_le: dict[str, datetime] = {}

    # --- préparation des cas ---------------------------------------------------
    def rendre(self, apprenant, chaine, maintenant, cohorte="COH1", exercice="EX1") -> str:
        """Ce que fait SoumettreCopie : copie rendue, première étape et son échéance."""
        cid = f"C{len(self.copies) + 1}"
        self.copies[cid] = Copie(cid, apprenant, exercice, cohorte, self.type_, 1, Statut.RENDUE)
        etape = etape_suivante(chaine, None)
        self.etats[cid] = Etat(etape.value, maintenant + timedelta(hours=chaine.config(etape).delai_heures))
        self.rendues_le[cid] = maintenant
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

    def contenu(self, copie_id):
        return self.contenus.get(copie_id, Contenu("", "", "", "", ""))

    def completer_contenu(self, copie_id, texte, commit, instantane):
        self.contenus[copie_id] = replace(self.contenu(copie_id), texte=texte, commit=commit, instantane=instantane)

    def consigne(self, exercice):
        return self.consignes.get(exercice, "")

    def titre(self, exercice):
        return self.titres.get(exercice, exercice)

    def ajouter_proposition(self, copie_id, p):
        self.props.setdefault(copie_id, []).append(p)

    def propositions(self, copie_id, verrouillee=False):
        if verrouillee:
            self.lectures_verrouillees.append(("propositions", copie_id))
        return self.props.get(copie_id, [])

    def courante(self, copie_id):
        return copie_id not in self.non_courantes

    def versions(self, copie_id):
        c = self.copies[copie_id]
        return [{"copie": v.id, "version": v.version, "rendue_le": self.rendues_le.get(v.id)}
                for v in sorted(self.copies.values(), key=lambda v: v.version)
                if v.apprenant == c.apprenant and v.exercice == c.exercice and v.version < c.version]

    def changer_statut(self, copie_id, statut, etape, echeance):
        self.copies[copie_id] = replace(self.copies[copie_id], statut=statut)
        self.etats[copie_id] = replace(self.etats[copie_id], etape=etape, echeance=echeance)

    def annuler_relectures(self, copie_id):
        for r in self.relectures_de(copie_id, StatutRelecture.A_FAIRE):
            self.rel[r.id] = replace(r, statut=StatutRelecture.ANNULEE)

    # --- DepotChaine -------------------------------------------------------------
    def verrouiller(self, copie_id):
        self.verrous.append(copie_id)
        self.verrou_tenu = True  # jusqu'à la prochaine validation de la transaction
        return CopieVerrouillee(self.copies[copie_id], self.etats[copie_id])

    # réservation courte de la pré-correction : validée aussitôt (le verrou est rendu)
    def reserver_ia(self, copie_id, maintenant, peremption):
        self.verrouiller(copie_id)
        deja = any(p.source == Source.IA for p in self.propositions(copie_id, verrouillee=True))
        marque = self.reservations_ia.get(copie_id)
        libre = not deja and (marque is None or marque <= maintenant - peremption)
        if libre:
            self.reservations_ia[copie_id] = maintenant
        self.verrou_tenu = False
        self.evenements.append(("reservation validée" if libre else "réservation refusée", copie_id))
        return libre

    def liberer_ia(self, copie_id):
        self.reservations_ia.pop(copie_id, None)
        self.verrou_tenu = False
        self.evenements.append(("réservation levée", copie_id))

    def etat(self, copie_id):
        return self.etats[copie_id]

    def grille(self, copie_id):
        return GRILLE

    def copies_echues(self, maintenant):
        return sorted((cid for cid, e in self.etats.items()
                       if e.echeance is not None and e.echeance <= maintenant and self.copies[cid].statut in EN_COURS),
                      key=lambda cid: self.etats[cid].echeance)

    def fixer_butoir(self, copie_id, butoir):
        self.etats[copie_id] = replace(self.etats[copie_id], butoir=butoir)

    def escalader(self, copie_id, destinataire, echeance):
        self.etats[copie_id] = replace(self.etats[copie_id], escalade_a=destinataire, echeance=echeance)

    def marquer_souffrance(self, copie_id, depuis):
        self.etats[copie_id] = replace(self.etats[copie_id], souffrance_depuis=depuis, rappel_souffrance=depuis)

    def rappeler_souffrance(self, copie_id, quand):
        self.etats[copie_id] = replace(self.etats[copie_id], rappel_souffrance=quand)

    def lever_souffrance(self, copie_id):
        self.etats[copie_id] = replace(self.etats[copie_id], souffrance_depuis=None, rappel_souffrance=None)

    def copies_en_souffrance(self):
        return sorted(cid for cid, e in self.etats.items() if e.souffrance_depuis is not None)

    def titulaires(self, copie_id):
        return set(self.titulaires_)

    def equipe(self, copie_id):
        return EquipeEffective(tuple(sorted(self.titulaires_)), tuple(self.suppleants_), self.responsable_, {})

    # --- DepotRelectures ---------------------------------------------------------
    def copies_rendues(self, exercice, cohorte):
        return [c for c in self.copies.values()
                if c.exercice == exercice and c.cohorte == cohorte
                and c.statut not in (Statut.RENVOYEE, Statut.REMPLACEE)]

    def taille_cohorte(self, cohorte):
        return self.tailles.get(cohorte, 0)

    def relectures(self, exercice, cohorte, verrouillee=False):
        if verrouillee:
            self.lectures_verrouillees.append(("relectures", exercice))
        return [r for r in self.rel.values()
                if self.copies[r.copie].exercice == exercice and self.copies[r.copie].cohorte == cohorte]

    def relecture(self, relecture_id):
        return self.rel.get(relecture_id)

    def verrouiller_relecture(self, relecture_id):
        return self.rel.get(relecture_id)

    def echeances(self, copie_ids):
        return {cid: self.etats[cid].echeance for cid in copie_ids}

    def relectures_copie(self, copie_id):
        return self.relectures_de(copie_id)

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

    # --- correction, publication, retours ------------------------------------------
    def jures(self, copie_id):
        return set(self.jures_)

    def publier(self, copie_id, note, note_sur, reussite, resume, lien, differe):
        self.resultats[copie_id] = (note, note_sur, reussite)
        self.publications.append((copie_id, note, reussite, resume, lien, differe))
        if differe:
            self.differees_.add(copie_id)

    def differee(self, copie_id):
        return copie_id in self.differees_

    def copies_differees(self, apprenant=None):
        return [cid for cid in sorted(self.differees_) if apprenant in (None, self.copies[cid].apprenant)]

    def liberer(self, copie_id, reussite, resume, lien):
        self.differees_.discard(copie_id)
        self.liberations.append((copie_id, reussite, resume, lien))

    def resultat(self, copie_id):
        return self.resultats.get(copie_id)

    def dispensee(self, copie_id):
        return copie_id in self.dispensees

    def signalee(self, copie_id):
        return copie_id in self.signalees

    def texte_lisible(self, copie_id):
        return self.contenu(copie_id).texte

    def texte_compact(self, copie_id):
        return self.contenu(copie_id).texte

    def copies_en_correction(self, exercice=None, pour=None):
        self.filtres_correction.append(pour)
        return [cid for cid, c in self.copies.items()
                if c.statut in (Statut.A_CORRIGER, Statut.PROVISOIRE) and self.etats[cid].etape
                and exercice in (None, c.exercice)
                and (pour is None or (self.titulaires_ | self.jures_ | {self.etats[cid].escalade_a}) & pour)]

    def copies_publiees(self, exercice=None):
        return [cid for cid, c in self.copies.items() if c.statut == Statut.PUBLIEE and exercice in (None, c.exercice)]

    def relectures_du_relecteur(self, relecteur):
        return [r for r in self.rel.values() if r.relecteur == relecteur]

    def auto_evaluation(self, apprenant, exercice):
        return self.auto_evals.get((apprenant, exercice))

    def enregistrer_auto_evaluation(self, apprenant, exercice, niveaux):
        self.auto_evals[(apprenant, exercice)] = dict(niveaux)

    def inscrit(self, apprenant, exercice):
        return (apprenant, exercice) in self.inscrits

    def derniere_copie(self, apprenant, exercice):
        miennes = [c for c in self.copies.values() if c.apprenant == apprenant and c.exercice == exercice]
        return max(miennes, key=lambda c: c.version) if miennes else None

    # --- délégations ---------------------------------------------------------------
    def creer_delegation(self, d):
        did = f"D{len(self.delegations_) + 1}"
        self.delegations_[did] = d
        return did

    def delegation(self, delegation_id):
        return self.delegations_.get(delegation_id)

    def cours(self, exercice):
        return self.cours_.get(exercice)

    def revoquer_delegation(self, delegation_id):
        self.delegations_[delegation_id] = replace(self.delegations_[delegation_id], revoquee=True)
