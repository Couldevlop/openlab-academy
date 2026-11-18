"""Journée 09 : ancienneté en mois révolus."""


def anciennete_en_mois(embauche, aujourdhui):
    """Rend le nombre de mois révolus entre les deux dates."""
    if embauche > aujourdhui:
        raise ValueError("la date d'embauche ne peut pas être dans le futur")
    mois = (aujourdhui.year - embauche.year) * 12 + aujourdhui.month - embauche.month
    if aujourdhui.day < embauche.day:
        mois -= 1
    return mois
