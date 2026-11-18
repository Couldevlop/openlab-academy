"""Le cœur métier : des calculs purs, que Django réutilise sans les réécrire."""

ESPACE = "\u00a0"
MOIS_REQUIS = 12


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


def etat_par_poste(effectif):
    """Rend, par poste, le nombre de salariés et la masse salariale."""
    totaux = {}
    for fiche in effectif:
        nombre, masse = totaux.get(fiche["poste"], (0, 0))
        totaux[fiche["poste"]] = (nombre + 1, masse + fiche["salaire_fcfa"])
    return {poste: {"effectif": nombre, "masse_fcfa": masse}
            for poste, (nombre, masse) in sorted(totaux.items())}
