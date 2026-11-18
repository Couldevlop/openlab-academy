"""La mise en forme pour un humain : ce module importe les calculs, jamais l'inverse."""
from rh.calculs import masse_salariale

ENTETE = f"{'Poste':<12}{'Nb':>4}{'Masse':>12}"


def etat_par_poste(effectif):
    """Rend l'état par poste, en une chaîne de plusieurs lignes."""
    lignes = [ENTETE]
    groupes = {}
    for fiche in effectif:
        groupes.setdefault(fiche["poste"], []).append(fiche["salaire_fcfa"])
    for poste in sorted(groupes):
        salaires = groupes[poste]
        lignes.append(f"{poste:<12}{len(salaires):>4}{masse_salariale(salaires):>12}")
    return "\n".join(lignes)
