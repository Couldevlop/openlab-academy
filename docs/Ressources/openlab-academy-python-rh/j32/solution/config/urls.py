"""Les adresses du projet."""
from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("connexion/", auth.LoginView.as_view(template_name="effectif/connexion.html"),
         name="connexion"),
    path("deconnexion/", auth.LogoutView.as_view(), name="deconnexion"),
    path("", include("effectif.urls")),
]
