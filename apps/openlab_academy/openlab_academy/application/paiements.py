"""Cas d'usage : ouvrir le dossier de paiement à l'inscription, choisir ou changer de mode."""
import re
from collections.abc import Callable
from datetime import date

from openlab_academy.application.ports_paiement import DepotDossiers, Journal, NouveauDossier, Reglages, Tarifs
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
