"""Les indicateurs de l'effectif : des calculs purs, affichables tels quels."""


def effectif_total(effectif):
    """Rend le nombre de salariés."""
    return len(effectif)


def masse_salariale(effectif):
    """Rend la somme des salaires de l'effectif."""
    return sum(fiche["salaire_fcfa"] for fiche in effectif)


def salaire_median(effectif):
    """Rend le salaire médian, ou 0 sur un effectif vide.

    La médiane dit mieux que la moyenne ce que gagne un salarié ordinaire : un seul très haut
    salaire ne la déplace pas.
    """
    if not effectif:
        return 0
    salaires = sorted(fiche["salaire_fcfa"] for fiche in effectif)
    milieu = len(salaires) // 2
    if len(salaires) % 2:
        return salaires[milieu]
    return (salaires[milieu - 1] + salaires[milieu]) // 2
