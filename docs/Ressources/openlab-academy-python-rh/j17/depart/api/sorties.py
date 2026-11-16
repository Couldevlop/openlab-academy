"""Les modèles de sortie : ce que l'API accepte de montrer, et rien de plus.

Décrivez ici les deux formes de sortie de l'énoncé.
"""
from pydantic import BaseModel


class SalarieResume(BaseModel):
    """Ce que la liste publique montre d'un salarié : jamais son salaire."""


class SalarieDetail(BaseModel):
    """Le détail d'un salarié, pour qui demande une fiche précise."""
