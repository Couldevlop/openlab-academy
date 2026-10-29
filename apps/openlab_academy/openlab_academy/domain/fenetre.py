"""Domaine : fenêtre d'accès d'un parcours limité aux dates de sa cohorte."""
import calendar
import datetime
from dataclasses import dataclass


class FenetreInvalide(ValueError):
    """La fin de la fenêtre précède son début."""


@dataclass(frozen=True)
class Fenetre:
    debut: datetime.date
    fin: datetime.date

    def __post_init__(self):
        if self.fin < self.debut:
            raise FenetreInvalide("la fin de la fenêtre précède son début")

    def ouverte(self, jour: datetime.date) -> bool:
        return self.debut <= jour <= self.fin

    def terminee(self, jour: datetime.date) -> bool:
        return jour > self.fin


def un_mois_apres(d: datetime.date) -> datetime.date:
    """Même jour du mois suivant, ramené au dernier jour du mois s'il n'existe pas."""
    annee, mois = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return datetime.date(annee, mois, min(d.day, calendar.monthrange(annee, mois)[1]))


def date_ouverture(reglee: datetime.date | None, aujourd_hui: datetime.date) -> datetime.date:
    """Date d'ouverture réglée ; vide ou passée, c'est le jour même."""
    return aujourd_hui if reglee is None or reglee < aujourd_hui else reglee
