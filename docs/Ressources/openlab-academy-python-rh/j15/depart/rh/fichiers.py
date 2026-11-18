"""La lecture de fichiers, et la traduction des pannes en erreurs métier."""
import csv
from pathlib import Path

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
        salaire = int(ligne["salaire_fcfa"])
    except ValueError as erreur:
        raise DonneeInvalide(
            f"Salaire illisible ligne {numero} : {ligne['salaire_fcfa']!r}") from erreur
    return {"matricule": ligne["matricule"], "nom": ligne["nom"], "poste": ligne["poste"],
            "date_embauche": ligne["date_embauche"], "salaire_fcfa": salaire}
