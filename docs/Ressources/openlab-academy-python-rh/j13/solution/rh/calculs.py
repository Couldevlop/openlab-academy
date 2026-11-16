"""Le cœur métier : des calculs, et rien d'autre.

Ce module n'importe rien du projet, ni fichier, ni réseau, ni framework. C'est ce qui lui permet
de servir le programme en ligne de commande, l'API, l'écran et, plus tard, Django.
"""

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


def par_poste(effectif):
    """Rend les noms regroupés par poste."""
    groupes = {}
    for fiche in effectif:
        groupes.setdefault(fiche["poste"], []).append(fiche["nom"])
    return groupes
