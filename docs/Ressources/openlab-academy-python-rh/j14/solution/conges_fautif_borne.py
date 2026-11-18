"""Implémentation fautive : la borne des douze mois est exclue. Ne la modifiez pas."""

MOIS_REQUIS = 12


def droit_aux_conges(mois_anciennete):
    """Rend True si le droit aux congés est ouvert."""
    if mois_anciennete < 0:
        raise ValueError("une ancienneté ne peut pas être négative")
    return mois_anciennete > MOIS_REQUIS
