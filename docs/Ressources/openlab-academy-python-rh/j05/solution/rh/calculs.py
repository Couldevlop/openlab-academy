"""Journée 05 : les calculs de la semaine, regroupés."""

ESPACE = "\u00a0"
MOIS_REQUIS = 12


def salaire_annuel(mensuel, primes):
    """Rend le coût annuel, en francs CFA, en nombre entier."""
    return round(mensuel * 12 + sum(primes))


def formater_fcfa(montant):
    """Rend le montant écrit avec des espaces comme séparateurs de milliers."""
    return f"{round(montant):,} FCFA".replace(",", ESPACE)


def droit_aux_conges(mois_anciennete):
    """Rend True si le droit aux congés est ouvert."""
    if mois_anciennete < 0:
        raise ValueError("une ancienneté ne peut pas être négative")
    return mois_anciennete >= MOIS_REQUIS


def masse_salariale(salaires):
    """Rend la somme des salaires. Une liste vide vaut 0."""
    total = 0
    for salaire in salaires:
        total += salaire
    return total


def plus_haut_salaire(salaires):
    """Rend le salaire le plus élevé. Une liste vide lève une ValueError."""
    if not salaires:
        raise ValueError("un effectif vide n'a pas de plus haut salaire")
    plus_haut = salaires[0]
    for salaire in salaires:
        if salaire > plus_haut:
            plus_haut = salaire
    return plus_haut
