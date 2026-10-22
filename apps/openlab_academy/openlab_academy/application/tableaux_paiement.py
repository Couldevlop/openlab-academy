"""Vues de lecture du paiement : dossier de l'apprenant, intendance (indicateurs et lignes), fiche, résumé, tableur.

Statuts, blocage, arriérés et encours viennent toujours du domaine (`statut`, `bloque`, `arriere`, `a_echoir`) : le
filtre de statut s'applique ici, après calcul, jamais en SQL. Les comptes d'apprenants sont des apprenants distincts.
"""
import calendar
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import date, timedelta

from openlab_academy.application.paiements import DossierAbsent, montant_a_payer
from openlab_academy.application.ports_paiement import (
    DepotDossiers, DossierEnregistre, FiltresTableau, LigneDossier, Tableaux)
from openlab_academy.domain.dossier_paiement import (
    Dossier, Statut, a_echoir, arriere, bloque, exigible, reste_du, statut)
from openlab_academy.domain.echeancier import Mode, Tarif

LIGNES_MAX = 5000  # lignes rendues au plus (vue et export) ; les indicateurs portent sur tous les dossiers filtrés
JOURNAL_FICHE = 200
DERNIERES_ACTIONS = 5
ENCOURS_JOURS = 30
TEXTE_MAX = 140
FORMULES = ("=", "+", "-", "@", "\t", "\r")
PLEINE_CHASSE = ("＝", "＋", "－", "＠")  # variantes pleine chasse, converties en formules par certains tableurs
LIBELLES_MODE = {Mode.UNE_FOIS: "Une fois", Mode.DEUX_TRANCHES: "Deux tranches", Mode.MENSUEL: "Mensuel"}
LIBELLES_STATUT = {Statut.A_JOUR: "À jour", Statut.EN_RETARD: "En retard", Statut.SOLDE: "Soldé",
                   Statut.DISPENSE: "Dispensé"}


class FiltreInvalide(ValueError):
    """Filtre refusé ; le message est destiné à l'agent."""


def _texte(valeur, nom: str) -> str | None:
    if valeur is None:
        return None
    if not isinstance(valeur, str) or len(valeur := valeur.strip()) > TEXTE_MAX:
        raise FiltreInvalide(f"Filtre « {nom} » invalide.")
    return valeur or None


def _choix(valeur, nom: str, enum):
    valeur = _texte(valeur, nom)
    try:
        return enum(valeur) if valeur else None
    except ValueError:
        raise FiltreInvalide(f"Filtre « {nom} » invalide.") from None


def _date(valeur, nom: str) -> date | None:
    valeur = _texte(valeur, nom)
    if valeur is None:
        return None
    try:
        if len(valeur) != 10:
            raise ValueError
        return date.fromisoformat(valeur)
    except ValueError:
        raise FiltreInvalide(f"Filtre « {nom} » : date attendue au format AAAA-MM-JJ.") from None


def lire_filtres(parcours=None, cohorte=None, mode=None, statut=None, du=None,
                 au=None) -> tuple[FiltresTableau, Statut | None]:
    """Filtres d'une requête : énumérations connues, dates ISO, période dans l'ordre ; vide = absent."""
    f = FiltresTableau(_texte(parcours, "parcours"), _texte(cohorte, "cohorte"), _choix(mode, "mode", Mode),
                       _date(du, "du"), _date(au, "au"))
    if f.du and f.au and f.du > f.au:
        raise FiltreInvalide("La période est invalide : « du » doit précéder « au ».")
    return f, _choix(statut, "statut", Statut)


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _tarif(t: Tarif) -> dict:
    return {"frais_inscription": t.frais_inscription, "une_fois": t.une_fois, "deux_tranches": t.deux_tranches,
            "mensuel": t.mensuel}


def _echeances(d: Dossier) -> list[dict]:
    return [{"date_limite": e.date_limite.isoformat(), "montant": e.montant, "libelle": e.libelle, "couverte": c}
            for e, c in d.couverture()]


def _prochaine(d: Dossier, aujourd_hui: date) -> dict | None:
    """Prochaine échéance non couverte et le montant que « Payer » demandera."""
    montant = montant_a_payer(d)
    if not montant:
        return None
    e = d.prochaine(aujourd_hui)
    return {"date_limite": _iso(e.date_limite if e else None), "montant": montant}


def vue_apprenant(d: DossierEnregistre, titre: str, aujourd_hui: date, en_ligne: bool,
                  instructions_virement: str | None = "") -> dict:
    """Dossier de l'apprenant connecté (le sien seulement : le point d'entrée le charge par la session), avec son
    blocage et les instructions de virement publiques des réglages (texte brut)."""
    return {"cours": d.cours, "titre": titre, "mode": d.mode.value, "telephone": d.telephone,
            "tarif": _tarif(d.tarif), "echeances": _echeances(d.dossier), "paye": d.dossier.paye,
            "reste": reste_du(d.dossier), "statut": statut(d.dossier, aujourd_hui).value,
            "prochaine": _prochaine(d.dossier, aujourd_hui), "paiement_en_ligne": en_ligne,
            "bloque": bloque(d.dossier, aujourd_hui), "instructions_virement": instructions_virement or ""}


def _ligne(x: LigneDossier, aujourd_hui: date) -> dict:
    return {"dossier": x.nom, "apprenant": x.apprenant, "nom": x.nom_complet, "email": x.email, "parcours": x.cours,
            "titre": x.titre, "cohorte": x.cohorte, "mode": x.mode.value, "paye": x.dossier.paye,
            "total": x.dossier.total, "reste": reste_du(x.dossier), "prochaine": _prochaine(x.dossier, aujourd_hui),
            "statut": statut(x.dossier, aujourd_hui).value, "bloque": bloque(x.dossier, aujourd_hui)}


def _rappel_envoye(x: LigneDossier, aujourd_hui: date, envoyes: frozenset[tuple[str, str]]) -> bool:
    """Un rappel est parti pour l'échéance que le dossier attend ensuite."""
    p = _prochaine(x.dossier, aujourd_hui)
    return bool(p and p["date_limite"] and (x.nom, p["date_limite"]) in envoyes)


def _apprenants(lignes: Iterable[LigneDossier], condition: Callable[[Dossier], bool]) -> int:
    return len({x.apprenant for x in lignes if condition(x.dossier)})


def _fin_du_mois(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


class Intendance:
    """Vue complète de l'intendant : indicateurs sur les dossiers filtrés, puis leurs lignes (avec, pour chacune,
    l'envoi d'un rappel pour sa prochaine échéance)."""

    def __init__(self, tableaux: Tableaux, aujourd_hui: Callable[[], date]):
        self._tableaux = tableaux
        self._aujourd_hui = aujourd_hui

    def executer(self, filtres: FiltresTableau, statut_filtre: Statut | None = None,
                 limite: int = LIGNES_MAX) -> dict:
        j = self._aujourd_hui()
        lignes = [x for x in self._tableaux.dossiers(filtres)
                  if statut_filtre is None or statut(x.dossier, j) is statut_filtre]
        restreint = filtres != FiltresTableau() or statut_filtre is not None
        noms = tuple(x.nom for x in lignes) if restreint else None
        encaisse = self._tableaux.encaisse(j.replace(day=1), _fin_du_mois(j), noms) if lignes else 0
        visibles = lignes[:limite]
        envoyes = self._tableaux.rappels_envoyes(tuple(x.nom for x in visibles)) if visibles else frozenset()
        return {
            "indicateurs": {
                "encaisse_mois": encaisse,
                "encours_30j": sum(a_echoir(x.dossier, j, ENCOURS_JOURS) for x in lignes),
                "en_retard": {"montant": sum(arriere(x.dossier, j) for x in lignes),
                              "apprenants": _apprenants(lignes, lambda d: arriere(d, j) > 0)},
                "bloques": _apprenants(lignes, lambda d: bloque(d, j)),
            },
            "lignes": [_ligne(x, j) | {"rappel_envoye": _rappel_envoye(x, j, envoyes)} for x in visibles],
            "tronque": len(lignes) > limite,
        }


class Fiche:
    """Fiche d'un dossier pour l'intendant : échéancier, paiements, rappels, journal (qui, quoi, quand)."""

    def __init__(self, depot: DepotDossiers, tableaux: Tableaux, aujourd_hui: Callable[[], date]):
        self._depot = depot
        self._tableaux = tableaux
        self._aujourd_hui = aujourd_hui

    def executer(self, nom: str) -> dict:
        d = self._depot.par_nom(nom)
        x = self._tableaux.ligne(nom) if d else None
        if x is None:
            raise DossierAbsent("Aucun dossier de paiement pour ce parcours.")
        j = self._aujourd_hui()
        return _ligne(replace(x, dossier=d.dossier), j) | {
            "telephone": d.telephone, "tarif": _tarif(d.tarif), "inscription": d.inscription.isoformat(),
            "echeances": _echeances(d.dossier), "arriere": arriere(d.dossier, j), "dispense": d.dossier.dispense,
            "delai_jusqu_au": _iso(d.dossier.delai_jusqu_au),
            "paiements": list(self._tableaux.paiements(nom)), "rappels": list(self._tableaux.rappels(nom)),
            "journal": list(self._tableaux.journal(nom, JOURNAL_FICHE)),
        }


def _pourcentage(part: int, base: int) -> float | None:
    return round(part * 100 / base, 1) if base else None


class Resume:
    """Résumé de l'administration : encaissé du mois et évolution, recouvrement, retards, parcours, modes."""

    def __init__(self, tableaux: Tableaux, aujourd_hui: Callable[[], date]):
        self._tableaux = tableaux
        self._aujourd_hui = aujourd_hui

    def executer(self) -> dict:
        j = self._aujourd_hui()
        lignes = self._tableaux.dossiers(FiltresTableau())
        mois = self._tableaux.encaisse(j.replace(day=1), _fin_du_mois(j))  # même mesure que l'intendance
        precedent = (j.replace(day=1) - timedelta(days=1)).replace(day=1)
        reference = self._tableaux.encaisse(precedent, precedent.replace(day=min(j.day, _fin_du_mois(precedent).day)))
        du = sum(exigible(x.dossier, j) for x in lignes)
        recouvre = sum(min(x.dossier.paye, exigible(x.dossier, j)) for x in lignes)
        parcours: dict[str, dict] = {}
        for x in lignes:
            p = parcours.setdefault(x.cours, {"parcours": x.cours, "titre": x.titre, "inscrits": 0, "encaisse": 0,
                                              "reste": 0})
            p["inscrits"] += 1
            p["encaisse"] += x.dossier.paye
            p["reste"] += reste_du(x.dossier)
        modes = Counter(x.mode for x in lignes)
        return {
            "encaisse_mois": mois,
            "evolution_pct": _pourcentage(mois - reference, reference),
            "taux_recouvrement": _pourcentage(recouvre, du),
            "retards": _apprenants(lignes, lambda d: arriere(d, j) > 0),
            "bloques": _apprenants(lignes, lambda d: bloque(d, j)),
            "par_parcours": sorted(parcours.values(), key=lambda p: (p["titre"], p["parcours"])),
            "modes": {m.value: modes[m] for m in Mode},
            "dernieres_actions": list(self._tableaux.journal(None, DERNIERES_ACTIONS)),
        }


def neutraliser(valeur):
    """Cellule de tableur : un texte commençant (blancs de tête ignorés) par =, +, -, @, leurs variantes pleine chasse,
    une tabulation ou un retour est préfixé d'une apostrophe (injection de formule) ; None devient vide ; les nombres
    restent des nombres."""
    if valeur is None:
        return ""
    if isinstance(valeur, str) and (valeur.startswith(FORMULES)
                                    or valeur.lstrip().startswith(FORMULES + PLEINE_CHASSE)):
        return "'" + valeur
    return valeur


ENTETES = ["Dossier", "Apprenant", "Nom", "E-mail", "Parcours", "Cohorte", "Mode", "Payé", "Total", "Reste",
           "Prochaine échéance", "Montant prochaine", "Statut", "Bloqué"]


def tableur(lignes: Iterable[dict]) -> list[list]:
    """Lignes de l'intendance en tableau (en-têtes d'abord), cellules neutralisées."""
    rangees = [ENTETES]
    for x in lignes:
        p = x["prochaine"] or {}
        rangees.append([neutraliser(v) for v in (
            x["dossier"], x["apprenant"], x["nom"], x["email"], x["titre"], x["cohorte"],
            LIBELLES_MODE[Mode(x["mode"])], x["paye"], x["total"], x["reste"], p.get("date_limite"),
            p.get("montant"), LIBELLES_STATUT[Statut(x["statut"])], "oui" if x["bloque"] else "non")])
    return rangees
