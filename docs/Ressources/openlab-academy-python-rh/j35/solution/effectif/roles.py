"""Les rôles de l'application : qui a le droit de voir quoi.

Un rôle n'est pas un affichage : la réponse envoyée doit changer, sinon la donnée part quand même
sur le réseau et un simple affichage du code source la révèle.
"""
GROUPE_RH = "Équipe RH"
GROUPE_MANAGER = "Managers"


def voit_les_salaires(utilisateur):
    """Rend True si cet utilisateur a le droit de voir les rémunérations."""
    if not utilisateur.is_authenticated:
        return False
    return utilisateur.is_superuser or utilisateur.groups.filter(name=GROUPE_RH).exists()
