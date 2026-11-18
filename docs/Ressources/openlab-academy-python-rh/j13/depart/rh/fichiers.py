"""La lecture de fichiers, et la traduction des pannes en erreurs métier.

Reprenez votre chargement de la journée 12, et attrapez les trois pannes de l'énoncé.
"""
import csv
from pathlib import Path

from rh.erreurs import DonneeInvalide

COLONNES = ("matricule", "nom", "poste", "date_embauche", "salaire_fcfa")


def charger_effectif(chemin):
    """Rend la liste des fiches lues dans le fichier CSV, ou lève DonneeInvalide."""
    raise NotImplementedError("à écrire")
