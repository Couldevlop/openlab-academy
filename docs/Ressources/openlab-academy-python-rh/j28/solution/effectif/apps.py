"""Déclaration de l'application effectif."""
from django.apps import AppConfig


class EffectifConfig(AppConfig):
    """L'application qui tient l'effectif et ses absences."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "effectif"
    verbose_name = "Effectif"
