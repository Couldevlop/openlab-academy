"""Les erreurs métier : ce que l'utilisateur peut corriger lui-même."""


class DonneeInvalide(Exception):
    """La donnée fournie ne peut pas être exploitée telle quelle."""


class DejaPris(Exception):
    """Le matricule demandé est déjà attribué."""


class Introuvable(Exception):
    """Le salarié demandé n'existe pas dans le dépôt."""
