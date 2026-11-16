"""La préparation des données affichées : des fonctions pures, testables sans écran."""

COLONNES = ("matricule", "nom", "poste")


def colonnes_affichees(effectif):
    """Rend les lignes à afficher, limitées aux colonnes publiques."""
    return [{colonne: fiche[colonne] for colonne in COLONNES} for fiche in effectif]
