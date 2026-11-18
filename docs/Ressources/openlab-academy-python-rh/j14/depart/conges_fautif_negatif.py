"""Implémentation fautive : une ancienneté négative passe sans rien dire. Ne la modifiez pas."""

MOIS_REQUIS = 12


def droit_aux_conges(mois_anciennete):
    """Rend True si le droit aux congés est ouvert."""
    return mois_anciennete >= MOIS_REQUIS
