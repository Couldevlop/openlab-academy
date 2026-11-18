"""La préparation des données affichées : des fonctions pures, testables sans écran."""

COLONNES = ("matricule", "nom", "poste")


def colonnes_affichees(effectif):
    """Rend les lignes à afficher, limitées aux colonnes publiques."""
    return [{colonne: fiche[colonne] for colonne in COLONNES} for fiche in effectif]


def postes(effectif):
    """Rend la liste des postes présents, triée, sans doublon."""
    raise NotImplementedError("à écrire")


def filtrer(effectif, poste=None, salaire_minimum=0):
    """Rend les fiches du poste demandé dont le salaire atteint le minimum."""
    raise NotImplementedError("à écrire")
