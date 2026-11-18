"""Journée 26 : un projet qui démarre, et qui ne porte aucun secret."""
import pathlib

from django.apps import apps
from django.conf import settings
from django.core.management import call_command


def test_l_application_effectif_est_declaree():
    assert apps.is_installed("effectif")


def test_la_verification_de_django_ne_signale_rien():
    call_command("check")


def test_le_mode_debug_est_eteint_par_defaut():
    assert settings.DEBUG is False


def test_la_clef_vient_de_l_environnement():
    source = pathlib.Path("config/settings.py").read_text(encoding="utf-8")
    assert "DJANGO_SECRET_KEY" in source
    assert "django-insecure" not in source


def test_le_mode_debug_vient_de_l_environnement():
    assert "DJANGO_DEBUG" in pathlib.Path("config/settings.py").read_text(encoding="utf-8")


def test_le_coeur_pur_est_toujours_la():
    from rh.calculs import masse_salariale
    assert masse_salariale([1, 2]) == 3
