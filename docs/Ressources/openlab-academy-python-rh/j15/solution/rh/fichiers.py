"""La lecture de fichiers, et la traduction des pannes en erreurs métier."""
import csv
from pathlib import Path

from pydantic import ValidationError

from rh.entrees import SalarieEntrant
from rh.erreurs import DonneeInvalide

COLONNES = ("matricule", "nom", "poste", "date_embauche", "salaire_fcfa")


def charger_effectif(chemin):
    """Rend la liste des fiches lues dans le fichier CSV, ou lève DonneeInvalide."""
    fichier = Path(chemin)
    try:
        texte = fichier.open(encoding="utf-8", newline="")
    except FileNotFoundError as erreur:
        raise DonneeInvalide(f"Fichier introuvable : {fichier}") from erreur
    fiches = []
    with texte:
        for numero, ligne in enumerate(csv.DictReader(texte), start=2):
            fiches.append(_fiche(ligne, numero, fichier))
    return fiches


def _fiche(ligne, numero, fichier):
    """Rend une fiche à partir d'une ligne lue, ou lève DonneeInvalide."""
    for colonne in COLONNES:
        if ligne.get(colonne) is None:
            raise DonneeInvalide(f"Colonne {colonne} absente du fichier {fichier}.")
    try:
        entrant = SalarieEntrant(**{colonne: ligne[colonne] for colonne in COLONNES})
    except ValidationError as erreur:
        champ = erreur.errors()[0]["loc"][0]
        raise DonneeInvalide(f"Ligne {numero} du fichier {fichier} : champ {champ} invalide.") from erreur
    fiche = entrant.model_dump()
    fiche["date_embauche"] = fiche["date_embauche"].isoformat()
    return fiche
