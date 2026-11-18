"""Le modèle d'entrée : ce que le monde extérieur a le droit d'envoyer.

Décrivez ici les cinq champs attendus et leurs contraintes, puis branchez le modèle sur le
chargement de rh/fichiers.py.
"""
from pydantic import BaseModel


class SalarieEntrant(BaseModel):
    """Une fiche venue de l'extérieur, avant d'entrer dans le cœur."""
