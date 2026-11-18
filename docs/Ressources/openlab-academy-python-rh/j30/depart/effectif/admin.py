"""L'administration : le back-office de l'équipe RH, pas une porte de service."""
from django.contrib import admin

from effectif.models import Absence, Poste, Salarie


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    """Les postes, par libellé."""

    list_display = ("libelle",)
    search_fields = ("libelle",)


@admin.register(Salarie)
class SalarieAdmin(admin.ModelAdmin):
    """Les salariés, avec leur poste et leur date d'embauche."""

    list_display = ("matricule", "nom", "poste", "date_embauche")
    list_filter = ("poste",)
    search_fields = ("matricule", "nom")
    list_select_related = ("poste",)
    ordering = ("matricule",)


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    """Les absences, de la plus récente à la plus ancienne."""

    list_display = ("salarie", "date_debut", "date_fin", "motif")
    list_filter = ("date_debut",)
    list_select_related = ("salarie",)
