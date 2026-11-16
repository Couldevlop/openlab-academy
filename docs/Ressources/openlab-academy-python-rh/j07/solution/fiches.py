"""Journée 07 : la fiche salarié, en dictionnaire."""

CHAMPS = ("nom", "poste", "date_embauche", "salaire_fcfa")


def salarie(nom, poste, date_embauche, salaire_fcfa):
    """Rend la fiche d'un salarié, avec les quatre champs du parcours."""
    return {"nom": nom, "poste": poste, "date_embauche": date_embauche,
            "salaire_fcfa": salaire_fcfa}


def lire_champ(fiche, champ, defaut=None):
    """Rend la valeur du champ, ou la valeur par défaut si le champ est absent."""
    return fiche.get(champ, defaut)
