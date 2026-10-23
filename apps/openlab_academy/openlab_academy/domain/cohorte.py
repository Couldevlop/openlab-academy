"""Domaine : une cohorte (promotion) qui suit un parcours à dates fixes, selon un rythme réglé par l'administration."""
import datetime
from dataclasses import dataclass

from openlab_academy.domain.parcours import Parcours
from openlab_academy.domain.reglages import Reglages, Rythme


class CohorteInvalide(ValueError):
    """Un invariant de la cohorte n'est pas respecté."""


def _heure(hhmm: str) -> str:
    """« 18:30 » -> « 18 h 30 », « 19:00 » -> « 19 h »."""
    heures, minutes = hhmm.split(":")
    return f"{int(heures)} h" if minutes == "00" else f"{int(heures)} h {minutes}"


@dataclass(frozen=True)
class Cohorte:
    titre: str
    cours: str
    debut: datetime.date
    fin: datetime.date
    heure_debut: str
    heure_fin: str
    fuseau: str
    rythme: Rythme
    places: int = 30

    def __post_init__(self):
        if self.fin <= self.debut:
            raise CohorteInvalide("la fin doit suivre le début")
        if self.heure_fin <= self.heure_debut:
            raise CohorteInvalide("horaire incohérent : la séance doit finir après son début")
        if self.places <= 0:
            raise CohorteInvalide("il faut au moins une place")

    @property
    def seances(self) -> str:
        fuseau = "heure d'Abidjan" if self.fuseau == "Africa/Abidjan" else f"fuseau {self.fuseau}"
        return f"Séances de {_heure(self.heure_debut)} à {_heure(self.heure_fin)} ({fuseau})."

    @classmethod
    def pilote(cls, parcours: Parcours, debut: datetime.date, rythme: Rythme, reglages: Reglages) -> "Cohorte":
        """Promo 1 : séances et fuseau réglés ; durée calée sur la charge du parcours et le rythme choisi."""
        return cls(
            titre=f"Promo 1 — {parcours.title} · {rythme.libelle} {rythme.heures} h", cours=parcours.title,
            debut=debut, fin=debut + datetime.timedelta(weeks=parcours.duree_semaines(rythme.heures)),
            heure_debut=reglages.heure_debut, heure_fin=reglages.heure_fin, fuseau=reglages.fuseau, rythme=rythme,
            places=reglages.places_par_cohorte,
        )
