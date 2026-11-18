"""Les modèles de sortie : ce que l'API accepte de montrer, et rien de plus."""
from datetime import date

from pydantic import BaseModel


class SalarieResume(BaseModel):
    """Ce que la liste publique montre d'un salarié : jamais son salaire."""

    matricule: str
    nom: str
    poste: str


class SalarieDetail(BaseModel):
    """Le détail d'un salarié, pour qui demande une fiche précise."""

    matricule: str
    nom: str
    poste: str
    date_embauche: date
    salaire_fcfa: int
