"""Domaine : échéancier de paiement d'un parcours (frais d'inscription, trois modes, échéances le 10 du mois).
Montants en XOF entiers, multiples de 5 ; aucune dépendance Frappe."""
import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

PAS = 5


class Mode(StrEnum):
    UNE_FOIS = "une_fois"
    DEUX_TRANCHES = "deux_tranches"
    MENSUEL = "mensuel"


class TarifInvalide(ValueError):
    pass


@dataclass(frozen=True)
class Tarif:
    frais_inscription: int
    une_fois: int
    deux_tranches: int
    mensuel: int

    def prix(self, mode: Mode) -> int:
        return {Mode.UNE_FOIS: self.une_fois, Mode.DEUX_TRANCHES: self.deux_tranches,
                Mode.MENSUEL: self.mensuel}[mode]

    def valider(self) -> None:
        montants = (self.frais_inscription, self.une_fois, self.deux_tranches, self.mensuel)
        if any(m <= 0 for m in montants):
            raise TarifInvalide("Les montants doivent être strictement positifs.")
        if any(m % PAS for m in montants):
            raise TarifInvalide(f"Les montants doivent être des multiples de {PAS} XOF.")
        if not self.une_fois < self.deux_tranches < self.mensuel:
            raise TarifInvalide("Les prix doivent croître : une fois < deux tranches < mensuel.")
        if self.frais_inscription >= self.une_fois:
            raise TarifInvalide("Les frais d'inscription doivent être inférieurs à chaque prix.")


@dataclass(frozen=True)
class Echeance:
    date_limite: date
    montant: int
    libelle: str


def _jour_du_mois(annee: int, mois: int, jour: int) -> date:
    return date(annee + (mois - 1) // 12, (mois - 1) % 12 + 1, jour)


def dixieme_suivant(d: date, jour: int = 10) -> date:
    """Le `jour` du mois qui suit `d`."""
    return _jour_du_mois(d.year, d.month + 1, jour)


def _prochain_jour(d: date, jour: int) -> date:
    """Le prochain `jour` du mois strictement postérieur à `d`."""
    return date(d.year, d.month, jour) if d.day < jour else dixieme_suivant(d, jour)


def _dates(mode: Mode, premiere: date, debut: date, fin: date, jour: int) -> list[date]:
    """Dates d'échéance du mode, à partir de la première."""
    if mode is Mode.UNE_FOIS:
        return [premiere]
    if mode is Mode.DEUX_TRANCHES:
        milieu = debut + (fin - debut) // 2
        seconde = date(milieu.year, milieu.month, jour)
        return [premiere, seconde if seconde > premiere else dixieme_suivant(premiere, jour)]
    dates, courante = [premiere], premiere
    while (courante.year, courante.month) < (fin.year, fin.month):
        courante = dixieme_suivant(courante, jour)
        dates.append(courante)
    return dates


def _repartir(reste: int, n: int) -> list[int]:
    """`n` parts multiples de 5 ; le reliquat va à la dernière."""
    part = (reste // n) // PAS * PAS
    return [part] * (n - 1) + [reste - part * (n - 1)]


def _lignes(dates: list[date], reste: int) -> list[Echeance]:
    return [Echeance(d, m, "Échéance") for d, m in zip(dates, _repartir(reste, len(dates)))]


def echeancier(mode: Mode, tarif: Tarif, inscription: date, debut: date, fin: date,
               jour: int = 10) -> tuple[Echeance, ...]:
    frais = Echeance(inscription, tarif.frais_inscription, "Frais d'inscription")
    reste = tarif.prix(mode) - tarif.frais_inscription
    return (frais, *_lignes(_dates(mode, dixieme_suivant(inscription, jour), debut, fin, jour), reste))


def replanifier(mode: Mode, tarif: Tarif, deja_paye: int, aujourd_hui: date, debut: date, fin: date,
                jour: int = 10) -> tuple[Echeance, ...]:
    """Nouveau calendrier après changement de mode : le déjà versé (plafonné au prix), puis le reste dû."""
    prix = tarif.prix(mode)
    verse = min(deja_paye, prix)
    lignes = [Echeance(aujourd_hui, verse, "Déjà versé")] if verse else []
    if prix > verse:
        lignes += _lignes(_dates(mode, _prochain_jour(aujourd_hui, jour), debut, fin, jour), prix - verse)
    return tuple(lignes)


def inscription_permise(debut: date, aujourd_hui: date, mois: int = 2) -> bool:
    """Vrai jusqu'à `mois` mois après le début de la cohorte (jour inclus, borné à la fin du mois)."""
    base = _jour_du_mois(debut.year, debut.month + mois, 1)
    limite = base.replace(day=min(debut.day, calendar.monthrange(base.year, base.month)[1]))
    return aujourd_hui <= limite
