"""Journée 08 : un effectif, en liste de fiches."""


def par_poste(effectif):
    """Rend les noms regroupés par poste."""
    groupes = {}
    for fiche in effectif:
        groupes.setdefault(fiche["poste"], []).append(fiche["nom"])
    return groupes


def filtrer_par_salaire(effectif, mini):
    """Rend les fiches dont le salaire atteint le minimum, borne comprise."""
    return [fiche for fiche in effectif if fiche["salaire_fcfa"] >= mini]
