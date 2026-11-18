"""Les adresses de l'application effectif."""
from django.urls import path

from effectif import vues

urlpatterns = [
    path("", vues.liste_salaries, name="salaries"),
    path("embauche/", vues.embaucher, name="embauche"),
    path("salaries/<str:matricule>/", vues.fiche_salarie, name="fiche-salarie"),
]
