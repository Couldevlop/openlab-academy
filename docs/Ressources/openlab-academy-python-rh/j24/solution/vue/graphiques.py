"""Les données des graphiques : encore des fonctions pures, sans dépendance à l'écran."""
from rh.calculs import etat_par_poste


def serie_masse_par_poste(effectif):
    """Rend {poste: masse}, dans l'ordre alphabétique, pour un graphique en barres."""
    return {poste: mesures["masse_fcfa"] for poste, mesures in etat_par_poste(effectif).items()}


def libelle_axe(montant_maximum):
    """Rend l'unité à écrire sur l'axe, pour que les barres restent lisibles.

    Un axe en unités brutes affiche des nombres à sept chiffres, illisibles de loin : on passe en
    milliers, puis en millions, quand la plus grande barre le justifie.
    """
    if montant_maximum >= 1_000_000:
        return "millions de FCFA"
    if montant_maximum >= 10_000:
        return "milliers de FCFA"
    return "FCFA"
