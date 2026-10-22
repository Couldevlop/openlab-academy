"""Cas d'usage : rappels de paiement J-7, J-3, J-1 par e-mail, SMS et WhatsApp.

Les rappels dus sont ceux du domaine (`rappels_dus`). Chaque envoi (dossier, échéance, délai, canal) est consigné
au registre et ne part qu'une fois : un rappel `envoye` n'est jamais renvoyé, même si la tâche tourne deux fois. Un
canal non configuré, ou un destinataire sans adresse pour ce canal, est `ignore` ; un canal en erreur est `echec`,
consigné sans secret, et n'empêche ni les autres canaux ni les autres apprenants. Un rappel en `echec` est relancé
aux passages suivants tant que l'échéance n'est ni passée ni couverte, et qu'aucun rappel plus récent du même canal
ne l'a remplacé.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from openlab_academy.domain.dossier_paiement import Dossier, rappels_dus

ENVOYE, ECHEC, IGNORE = "envoye", "echec", "ignore"


@dataclass(frozen=True)
class Destinataire:
    email: str
    telephone: str
    nom: str


@dataclass(frozen=True)
class Message:
    sujet: str
    texte: str
    parametres: tuple[str, ...]


class EnvoiImpossible(Exception):
    """Canal en erreur ; le message, construit par l'adaptateur, ne contient ni secret ni numéro."""


class DestinataireInjoignable(Exception):
    """Le destinataire n'a pas d'adresse pour ce canal (rappel ignoré, pas en échec)."""


class Canal(Protocol):
    nom: str

    def disponible(self) -> bool: ...
    def envoyer(self, destinataire: Destinataire, message: Message) -> None: ...


@dataclass(frozen=True)
class DossierARappeler:
    nom: str
    cours: str
    titre: str
    destinataire: Destinataire
    dossier: Dossier
    lien: str


class DepotRappels(Protocol):
    def noms(self) -> tuple[str, ...]:
        """Dossiers non dispensés."""

    def charger(self, nom: str) -> DossierARappeler | None: ...


class Registre(Protocol):
    def etats(self, dossier: str) -> dict[tuple[date, int, str], str]:
        """Statut de chaque rappel consigné du dossier, par (date limite, jours avant, canal)."""

    def reserver(self, dossier: str, date_limite: date, jours: int, canal: str) -> bool:
        """Réserve l'envoi (consigné `echec` d'ici sa conclusion) ; False s'il est déjà envoyé ou pris ailleurs."""

    def consigner(self, dossier: str, date_limite: date, jours: int, canal: str, statut: str) -> None: ...


def _montant(montant: int) -> str:
    return f"{montant:,}".replace(",", " ")


def message_rappel(titre: str, montant: int, date_limite: date, lien: str, nom: str) -> Message:
    jour = date_limite.strftime("%d/%m/%Y")
    texte = (f"Rappel OpenLab Academy : {_montant(montant)} FCFA à régler au plus tard le {jour} pour le parcours "
             f"{titre}. Payer : {lien}")
    return Message(f"Rappel de paiement : {titre}", texte, (nom or "apprenant", _montant(montant), jour))


def _sans_alerte(titre: str, detail: str) -> None:
    pass


def _direct(action):
    return action()


class EnvoyerRappels:
    """`unite` exécute une action dans sa propre transaction, validée aussitôt (annulée si elle lève) : la
    planification d'un dossier, la réservation d'un envoi (validée AVANT l'appel au canal), puis l'envoi avec son
    statut final. `fatales` (ex. délai de la tâche dépassé) ne sont jamais avalées."""

    def __init__(self, depot: DepotRappels, canaux, registre: Registre, aujourd_hui: Callable[[], date], *,
                 delais: tuple[int, ...] = (7, 3, 1), alerte: Callable[[str, str], None] = _sans_alerte,
                 unite: Callable = _direct, fatales: tuple[type[BaseException], ...] = ()):
        self._depot = depot
        self._canaux = {c.nom: c for c in canaux}
        self._registre = registre
        self._aujourd_hui = aujourd_hui
        self._delais = tuple(delais)
        self._alerte = alerte
        self._unite = unite
        self._fatales = tuple(fatales)

    def executer(self) -> int:
        """Nombre de rappels envoyés."""
        aujourd_hui = self._aujourd_hui()
        envoyes = 0
        for nom in self._depot.noms():
            try:
                envoyes += self._traiter(nom, aujourd_hui)
            except self._fatales:
                raise
            except Exception as e:  # le dossier suivant est traité quand même
                self._alerte("Rappels de paiement : dossier non traité", f"dossier {nom} : {type(e).__name__}")
        return envoyes

    def _traiter(self, nom: str, aujourd_hui: date) -> int:
        d, plan, etats = self._unite(lambda: self._planifier(nom, aujourd_hui))
        return sum(self._envoyer(d, cle, montant, etats.get(cle)) for cle, montant in sorted(plan.items()))

    def _planifier(self, nom: str, aujourd_hui: date):
        """(dossier, plan {(date limite, jours, canal): montant}, états consignés) ; plan vide si dossier absent."""
        d = self._depot.charger(nom)
        if d is None:
            return None, {}, {}
        etats = self._registre.etats(nom)
        plan = {}
        for (date_limite, jours), montant in _cumul(rappels_dus(d.dossier, aujourd_hui, self._delais)).items():
            for canal in self._canaux:
                plan[(date_limite, jours, canal)] = montant
        for (date_limite, jours, canal), statut in etats.items():
            if statut != ECHEC or canal not in self._canaux or date_limite < aujourd_hui:
                continue
            if any(dl == date_limite and c == canal and j < jours for dl, j, c in [*etats, *plan]):
                continue  # un rappel plus récent de ce canal (consigné ou dû ce jour) le remplace
            restant = _cumul(rappels_dus(d.dossier, aujourd_hui, ((date_limite - aujourd_hui).days,)))
            montant = sum(m for (dl, _), m in restant.items() if dl == date_limite)
            if montant:
                plan[(date_limite, jours, canal)] = montant
        return d, plan, etats

    def _consigner(self, d: DossierARappeler, cle: tuple[date, int, str], statut: str) -> None:
        self._unite(lambda: self._registre.consigner(d.nom, *cle, statut))

    def _envoyer(self, d: DossierARappeler, cle: tuple[date, int, str], montant: int, etat: str | None) -> int:
        date_limite, jours, nom_canal = cle
        if etat == ENVOYE:
            return 0
        canal = self._canaux[nom_canal]
        if not canal.disponible():
            if etat != IGNORE:
                self._consigner(d, cle, IGNORE)
            return 0
        if not self._unite(lambda: self._registre.reserver(d.nom, date_limite, jours, nom_canal)):
            return 0
        message = message_rappel(d.titre, montant, date_limite, d.lien, d.destinataire.nom)

        def envoyer():
            canal.envoyer(d.destinataire, message)
            self._registre.consigner(d.nom, date_limite, jours, nom_canal, ENVOYE)
        try:
            self._unite(envoyer)
        except self._fatales:
            raise
        except DestinataireInjoignable:
            self._consigner(d, cle, IGNORE)
            return 0
        except Exception as e:  # la réservation validée reste `echec` : relançable
            detail = str(e) if isinstance(e, EnvoiImpossible) else type(e).__name__
            self._alerte("Rappel de paiement non envoyé", f"{nom_canal}, dossier {d.nom} : {detail}")
            return 0
        return 1


def _cumul(rappels) -> dict[tuple[date, int], int]:
    """Échéances d'une même date réunies en un seul rappel (la clé du registre est la date limite)."""
    cumul: dict[tuple[date, int], int] = {}
    for r in rappels:
        cle = (r.echeance.date_limite, r.jours_avant)
        cumul[cle] = cumul.get(cle, 0) + r.montant
    return cumul
