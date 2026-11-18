"""La commande d'import : elle réutilise le cœur, elle ne le réécrit pas.

Écrivez ici la commande de l'énoncé.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Importe un effectif depuis un fichier CSV, sans créer de doublon."""

    help = "Importe un effectif depuis un fichier CSV."
