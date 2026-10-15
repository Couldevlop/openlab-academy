"""Domaine : une cohorte (promotion) qui suit un parcours à dates fixes, en soirée."""
import datetime
from dataclasses import dataclass
from enum import Enum

from openlab_academy.domain.parcours import Parcours

FUSEAU = "Africa/Abidjan"


class CohorteInvalide(ValueError):
    """Un invariant de la cohorte n'est pas respecté."""


class Rythme(Enum):
    """Format de cohorte : charge hebdomadaire et organisation de la semaine."""

    STANDARD = ("standard", "Standard", (("lundi", 2), ("mercredi", 2), ("vendredi", 2), ("samedi", 3), ("dimanche", 3)),
                "12 h par semaine : 2 h les lundi, mercredi et vendredi soir, 3 h le samedi et le dimanche")
    INTENSIF = ("intensif", "Intensif", (("lundi", 2), ("mardi", 2), ("mercredi", 2), ("jeudi", 2), ("vendredi", 2),
                                         ("samedi", 3), ("dimanche", 3)),
                "16 h par semaine : 2 h chaque soir de semaine, 3 h le samedi et le dimanche")

    def __new__(cls, code: str, libelle: str, semaine: tuple, descriptif: str):
        membre = object.__new__(cls)
        membre._value_ = code
        membre.libelle = libelle
        membre.semaine = semaine
        membre.descriptif = descriptif
        return membre

    @property
    def heures(self) -> int:
        return sum(h for _, h in self.semaine)


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

    def __post_init__(self):
        if self.fin <= self.debut:
            raise CohorteInvalide("la fin doit suivre le début")
        if self.heure_fin <= self.heure_debut:
            raise CohorteInvalide("horaire incohérent : la séance doit finir après son début")

    @classmethod
    def pilote(cls, parcours: Parcours, debut: datetime.date, rythme: Rythme = Rythme.STANDARD) -> "Cohorte":
        """Promo 1, séances du soir 18 h 30 – 20 h 30 ; durée calée sur la charge du parcours et le rythme."""
        return cls(
            titre=f"Promo 1 — {parcours.title} · {rythme.libelle} {rythme.heures} h", cours=parcours.title,
            debut=debut, fin=debut + datetime.timedelta(weeks=parcours.duree_semaines(rythme.heures)),
            heure_debut="18:30", heure_fin="20:30", fuseau=FUSEAU, rythme=rythme,
        )
