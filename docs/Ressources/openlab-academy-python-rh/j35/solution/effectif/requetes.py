"""Les requêtes de l'effectif : une question posée à la base, une seule fois."""
from django.db.models import Count, Sum

from effectif.models import Salarie


def masse_salariale_par_poste():
    """Rend, par libellé de poste, l'effectif et la masse salariale, en une requête.

    L'agrégat est calculé par la base : ramener toutes les fiches en mémoire pour les additionner
    coûte un aller-retour par ligne et ne tient pas sur un vrai effectif.
    """
    lignes = (Salarie.objects
              .values("poste__libelle")
              .annotate(effectif=Count("id"), masse_fcfa=Sum("salaire_fcfa"))
              .order_by("poste__libelle"))
    return {ligne["poste__libelle"]: {"effectif": ligne["effectif"],
                                      "masse_fcfa": ligne["masse_fcfa"]}
            for ligne in lignes}


def salaries_du_poste(libelle):
    """Rend les salariés d'un poste, le poste chargé avec eux."""
    return list(Salarie.objects.select_related("poste").filter(poste__libelle=libelle))
