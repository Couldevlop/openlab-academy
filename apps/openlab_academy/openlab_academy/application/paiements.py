"""Cas d'usage : ouvrir le dossier de paiement à l'inscription, choisir ou changer de mode, payer en ligne."""
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta

from openlab_academy.application.ports_paiement import (
    DepotDossiers, Journal, NouveauDossier, Passerelle, ReferenceDejaEnregistree, Reglages, Tarifs)
from openlab_academy.domain.dossier_paiement import statut
from openlab_academy.domain.echeancier import Echeance, Mode, Tarif, echeancier, inscription_permise, replanifier

LIBELLE_FRAIS = "Frais d'inscription"
_CI = re.compile(r"\+225\d{10}")
_E164 = re.compile(r"\+\d{8,15}")


class InscriptionTardive(Exception):
    pass


class TarifAbsent(Exception):
    pass


class DossierAbsent(Exception):
    pass


class TelephoneInvalide(ValueError):
    pass


def valider_telephone(brut: str) -> str:
    """`+225` et exactement 10 chiffres, ou E.164 générique ; les espaces sont ignorés."""
    numero = re.sub(r"\s+", "", brut or "")
    modele = _CI if numero.startswith("+225") else _E164
    if not modele.fullmatch(numero):
        raise TelephoneInvalide("Numéro de téléphone invalide (format international, ex. +2250700000000).")
    return numero


class OuvrirDossier:
    def __init__(self, depot: DepotDossiers, tarifs: Tarifs, reglages: Reglages, aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._tarifs = tarifs
        self._reglages = reglages
        self._aujourd_hui = aujourd_hui

    def verifier(self, cours: str, debut: date) -> Tarif:
        """Refuse l'inscription tardive ou sans tarif ; renvoie le tarif (validé) du parcours."""
        if not inscription_permise(debut, self._aujourd_hui(), self._reglages.charger().inscription_tardive_mois):
            raise InscriptionTardive("Les inscriptions à cette cohorte sont closes.")
        tarif = self._tarifs.charger(cours)
        if tarif is None:
            raise TarifAbsent("Ce parcours n'a pas encore de tarif : inscription impossible.")
        tarif.valider()
        return tarif

    def executer(self, apprenant: str, cours: str, cohorte: str, debut: date, fin: date) -> str:
        """Dossier provisoire en `une_fois` : prix figés, seule l'échéance des frais ; renvoie son nom."""
        existant = self._depot.charger(apprenant, cours)
        if existant:
            return existant.nom
        tarif = self.verifier(cours, debut)
        aujourd_hui = self._aujourd_hui()
        return self._depot.creer(NouveauDossier(
            apprenant, cours, cohorte, Mode.UNE_FOIS, tarif, aujourd_hui,
            (Echeance(aujourd_hui, tarif.frais_inscription, LIBELLE_FRAIS),)))


class ChoisirMode:
    def __init__(self, depot: DepotDossiers, journal: Journal, aujourd_hui: Callable[[], date], jour: int = 10):
        self._depot = depot
        self._journal = journal
        self._aujourd_hui = aujourd_hui
        self._jour = jour

    def executer(self, apprenant: str, cours: str, mode: str, telephone: str) -> tuple[Echeance, ...]:
        nouveau = Mode(mode)
        numero = valider_telephone(telephone)
        d = self._depot.charger(apprenant, cours)
        if d is None:
            raise DossierAbsent("Aucun dossier de paiement pour ce parcours.")
        if d.dossier.paye:
            echeances = replanifier(nouveau, d.tarif, d.dossier.paye, self._aujourd_hui(), d.debut, d.fin, self._jour)
        else:
            echeances = echeancier(nouveau, d.tarif, d.inscription, d.debut, d.fin, self._jour)
        self._depot.remplacer_echeances(d.nom, nouveau, echeances)
        self._depot.fixer_telephone(d.nom, numero)
        self._journal(d.nom, apprenant, "mode", {"mode": d.mode.value, "echeances": _resume(d.dossier.echeances)},
                      {"mode": nouveau.value, "echeances": _resume(echeances)})
        return echeances


def _resume(echeances) -> list[list]:
    return [[e.date_limite.isoformat(), e.montant, e.libelle] for e in echeances]


MOYEN_EN_LIGNE = "cinetpay"
RECONCILIATION_MAX = 5  # contrôles au plus par retour, même si des paiements abandonnés s'accumulent
ACTEUR_PASSERELLE = "CinetPay"


class PaiementIndisponible(Exception):
    """Paiement en ligne non configuré, injoignable ou réponse inexploitable ; message sans secret."""


class RienADu(Exception):
    pass


def _multiple_de_5(montant: int) -> int:
    return -(-montant // 5) * 5


class InitierPaiement:
    """Ouvre un paiement en ligne de la part due de la prochaine échéance (au moins les frais restants)."""

    def __init__(self, depot: DepotDossiers, passerelle: Passerelle, maintenant: Callable[[], datetime],
                 liens: Callable[[str], tuple[str, str]]):
        self._depot = depot
        self._passerelle = passerelle
        self._maintenant = maintenant
        self._liens = liens  # cours -> (URL de retour, URL de notification)

    def executer(self, apprenant: str, cours: str) -> str:
        if not self._passerelle.disponible():
            raise PaiementIndisponible("Le paiement en ligne n'est pas disponible pour le moment.")
        d = self._depot.charger(apprenant, cours)
        if d is None:
            raise DossierAbsent("Aucun dossier de paiement pour ce parcours.")
        dossier = d.dossier
        part = max(dossier.part_prochaine(), dossier.frais_inscription - dossier.paye)
        if dossier.dispense or part <= 0:
            raise RienADu("Aucun montant n'est dû sur ce parcours.")
        montant = _multiple_de_5(part)
        echeance = dossier.prochaine(self._maintenant().date())
        libelle = echeance.libelle if echeance else LIBELLE_FRAIS
        retour, notification = self._liens(cours)
        client = self._depot.client(apprenant)
        if d.telephone:
            client = replace(client, telephone=d.telephone)
        reference = f"OLA-{d.nom}-{self._maintenant():%Y%m%d%H%M%S%f}"
        self._depot.creer_paiement(d.nom, montant, MOYEN_EN_LIGNE, reference, "en_attente")
        try:
            return self._passerelle.initier(reference, montant, f"{cours} - {libelle}", client, retour, notification)
        except PaiementIndisponible:
            self._depot.marquer_echoue(MOYEN_EN_LIGNE, reference)
            raise


class ConfirmerPaiement:
    """Confirme un paiement en ligne après contrôle auprès de la passerelle, au montant vérifié ; idempotent."""

    def __init__(self, depot: DepotDossiers, passerelle: Passerelle, journal: Journal):
        self._depot = depot
        self._passerelle = passerelle
        self._journal = journal

    def executer(self, transaction: str) -> None:
        p = self._depot.paiement(MOYEN_EN_LIGNE, transaction)
        if p is None or p.statut == "confirme":
            return
        v = self._passerelle.verifier(transaction)
        if v.statut == "echoue":
            self._depot.marquer_echoue(MOYEN_EN_LIGNE, transaction)
            return
        if v.statut != "confirme" or v.montant <= 0:
            return
        if not self._depot.confirmer_paiement(MOYEN_EN_LIGNE, transaction, v.montant):
            return  # une notification concurrente l'a confirmé
        apres = self._depot.paye(p.dossier)
        self._journal(p.dossier, ACTEUR_PASSERELLE, "paiement_confirme",
                      {"statut": p.statut, "paye": apres - v.montant, "montant": p.montant},
                      {"statut": "confirme", "paye": apres, "montant": v.montant})

    def reconcilier(self, apprenant: str, cours: str, limite: int = RECONCILIATION_MAX) -> None:
        """Notification perdue : revérifie les paiements en ligne en attente de l'apprenant sur ce parcours.
        Une passerelle injoignable interrompt (PaiementIndisponible) ; les confirmations déjà faites restent."""
        d = self._depot.charger(apprenant, cours)
        if d is None:
            return
        for reference in self._depot.paiements_en_attente(d.nom, MOYEN_EN_LIGNE, limite):
            self.executer(reference)


REVERIFICATION_JOURS = 7


class ReverifierPaiements:
    """Tâche quotidienne : revérifie auprès de la passerelle les paiements en ligne encore en attente et créés il y a
    moins de 7 jours (notification perdue). Chaque paiement est indépendant : une erreur est consignée sans secret
    et les suivants sont traités ; une passerelle injoignable arrête le passage (inutile d'insister). `fatales`
    (ex. délai de la tâche dépassé) ne sont jamais avalées."""

    def __init__(self, depot: DepotDossiers, confirmer: ConfirmerPaiement, maintenant: Callable[[], datetime], *,
                 alerte: Callable[[str, str], None] = lambda titre, detail: None,
                 unite: Callable[[Callable[[], None]], None] = lambda action: action(),
                 fatales: tuple[type[BaseException], ...] = ()):
        self._depot = depot
        self._confirmer = confirmer
        self._maintenant = maintenant
        self._alerte = alerte
        self._unite = unite
        self._fatales = tuple(fatales)

    def executer(self) -> int:
        """Nombre de paiements contrôlés."""
        depuis = self._maintenant() - timedelta(days=REVERIFICATION_JOURS)
        controles = 0
        for reference in self._depot.paiements_en_attente_depuis(MOYEN_EN_LIGNE, depuis):
            controles += 1
            try:
                self._unite(lambda reference=reference: self._confirmer.executer(reference))
            except self._fatales:
                raise
            except PaiementIndisponible as e:
                self._alerte("Paiement en ligne non revérifié",
                             f"transaction {reference[:64]!r} : {e} ; passage interrompu")
                break
            except Exception as e:
                self._alerte("Paiement en ligne non revérifié", f"transaction {reference[:64]!r} : {type(e).__name__}")
        return controles


REFERENCE_MAX = 140
MOTIF_MAX = 500
MOYEN_VIREMENT = "virement"


class OperationRefusee(ValueError):
    """Saisie refusée d'un virement ou d'un délai ; le message est destiné à l'agent."""


def _motif(motif, obligatoire: bool) -> str:
    if motif is None and not obligatoire:
        motif = ""
    if not isinstance(motif, str):
        raise OperationRefusee("Le motif est invalide.")
    motif = motif.strip()
    if obligatoire and not motif:
        raise OperationRefusee("Le motif est obligatoire.")
    if len(motif) > MOTIF_MAX:
        raise OperationRefusee(f"Le motif est trop long ({MOTIF_MAX} caractères au plus).")
    return motif


def _jour(valeur) -> bool:
    return type(valeur) is date


def _charger_actif(depot: DepotDossiers, nom: str):
    d = depot.par_nom(nom)
    if d is None:
        raise DossierAbsent("Aucun dossier de paiement pour ce parcours.")
    if d.dossier.dispense:
        raise OperationRefusee("Ce dossier est dispensé de paiement : aucune opération possible.")
    return d


class EnregistrerVirement:
    """Enregistre un virement reçu (confirmé d'office, auteur = l'agent) ; référence unique, journalisé."""

    def __init__(self, depot: DepotDossiers, journal: Journal, aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._journal = journal
        self._aujourd_hui = aujourd_hui

    def executer(self, acteur: str, dossier: str, montant: int, reference: str, date_paiement: date,
                 motif: str = "") -> None:
        if type(montant) is not int or montant <= 0:
            raise OperationRefusee("Le montant doit être un nombre entier positif de francs CFA.")
        if not isinstance(reference, str) or not 1 <= len(reference := reference.strip()) <= REFERENCE_MAX:
            raise OperationRefusee(f"La référence du virement est obligatoire ({REFERENCE_MAX} caractères au plus).")
        aujourd_hui = self._aujourd_hui()
        if not _jour(date_paiement) or date_paiement > aujourd_hui:
            raise OperationRefusee("La date du virement est invalide ou dans le futur.")
        motif = _motif(motif, obligatoire=False)
        d = _charger_actif(self._depot, dossier)
        avant = {"paye": d.dossier.paye, "statut": statut(d.dossier, aujourd_hui).value}
        try:
            self._depot.enregistrer_virement(d.nom, montant, reference, date_paiement, acteur)
        except ReferenceDejaEnregistree:
            raise OperationRefusee("Cette référence de virement est déjà enregistrée.") from None
        apres = self._depot.par_nom(d.nom).dossier
        self._journal(d.nom, acteur, "virement_enregistre", avant,
                      {"paye": apres.paye, "statut": statut(apres, aujourd_hui).value, "montant": montant,
                       "reference": reference, "date_paiement": date_paiement.isoformat()}, motif)


class AccorderDelai:
    """Accorde un délai de paiement (et débloque ainsi l'apprenant jusqu'à cette date) ; motif obligatoire."""

    def __init__(self, depot: DepotDossiers, journal: Journal, aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._journal = journal
        self._aujourd_hui = aujourd_hui

    def executer(self, acteur: str, dossier: str, jusqu_au: date, motif: str) -> None:
        aujourd_hui = self._aujourd_hui()
        if not _jour(jusqu_au) or jusqu_au <= aujourd_hui:
            raise OperationRefusee("Le délai doit se terminer après aujourd'hui.")
        motif = _motif(motif, obligatoire=True)
        d = _charger_actif(self._depot, dossier)
        ancien = d.dossier.delai_jusqu_au
        avant = {"delai_jusqu_au": ancien.isoformat() if ancien else None,
                 "statut": statut(d.dossier, aujourd_hui).value}
        self._depot.fixer_delai(d.nom, jusqu_au)
        apres = self._depot.par_nom(d.nom).dossier
        self._journal(d.nom, acteur, "delai_accorde", avant,
                      {"delai_jusqu_au": jusqu_au.isoformat(), "statut": statut(apres, aujourd_hui).value}, motif)
