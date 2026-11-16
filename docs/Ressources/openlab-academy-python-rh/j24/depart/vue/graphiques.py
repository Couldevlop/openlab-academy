"""Les données des graphiques : encore des fonctions pures, sans dépendance à l'écran."""
from rh.calculs import etat_par_poste


def serie_masse_par_poste(effectif):
    """Rend {poste: masse}, dans l'ordre alphabétique, pour un graphique en barres."""
    raise NotImplementedError("à écrire")


def libelle_axe(montant_maximum):
    """Rend l'unité à écrire sur l'axe, pour que les barres restent lisibles."""
    raise NotImplementedError("à écrire")
