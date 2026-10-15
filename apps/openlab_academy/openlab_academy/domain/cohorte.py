"""Domaine : une cohorte (promotion) qui suit un parcours à dates fixes, en soirée."""
import datetime
from dataclasses import dataclass

from openlab_academy.domain.parcours import Parcours

FUSEAU = "Africa/Abidjan"


class CohorteInvalide(ValueError):
    """Un invariant de la cohorte n'est pas respecté."""


@dataclass(frozen=True)
class Cohorte:
    titre: str
    cours: str
    debut: datetime.date
    fin: datetime.date
    heure_debut: str
    heure_fin: str
    fuseau: str

    def __post_init__(self):
        if self.fin <= self.debut:
            raise CohorteInvalide("la fin doit suivre le début")
        if self.heure_fin <= self.heure_debut:
            raise CohorteInvalide("horaire incohérent : la séance doit finir après son début")

    @classmethod
    def pilote(cls, parcours: Parcours, debut: datetime.date) -> "Cohorte":
        """Promo 1, en soirée (18 h 30 – 20 h 30), durée calée sur la charge du parcours."""
        return cls(
            titre=f"Promo 1 — {parcours.title}", cours=parcours.title, debut=debut,
            fin=debut + datetime.timedelta(weeks=parcours.duree_semaines()),
            heure_debut="18:30", heure_fin="20:30", fuseau=FUSEAU,
        )
