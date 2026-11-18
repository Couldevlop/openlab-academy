"""Journée 10 : l'état par poste, aligné."""

ENTETE = f"{'Poste':<12}{'Nb':>4}{'Masse':>12}"


def normaliser(texte):
    """Rend le texte sans espaces superflus, en casse de titre."""
    return " ".join(texte.split()).title()


def etat_par_poste(effectif):
    """Rend l'état par poste, en une chaîne de plusieurs lignes."""
    totaux = {}
    for fiche in effectif:
        poste = normaliser(fiche["poste"])
        nombre, masse = totaux.get(poste, (0, 0))
        totaux[poste] = (nombre + 1, masse + fiche["salaire_fcfa"])
    lignes = [ENTETE]
    for poste in sorted(totaux):
        nombre, masse = totaux[poste]
        lignes.append(f"{poste:<12}{nombre:>4}{masse:>12}")
    return "\n".join(lignes)
