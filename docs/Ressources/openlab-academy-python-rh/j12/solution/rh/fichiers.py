"""La lecture de fichiers : la seule porte d'entrée des données dans le programme."""
import csv
from pathlib import Path

COLONNES = ("matricule", "nom", "poste", "date_embauche", "salaire_fcfa")


def charger_effectif(chemin):
    """Rend la liste des fiches lues dans le fichier CSV."""
    fiches = []
    with Path(chemin).open(encoding="utf-8", newline="") as fichier:
        for ligne in csv.DictReader(fichier):
            fiches.append({
                "matricule": ligne["matricule"],
                "nom": ligne["nom"],
                "poste": ligne["poste"],
                "date_embauche": ligne["date_embauche"],
                "salaire_fcfa": int(ligne["salaire_fcfa"]),
            })
    return fiches
