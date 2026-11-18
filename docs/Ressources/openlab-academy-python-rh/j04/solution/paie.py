"""Journée 04 : boucles et accumulation."""


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
