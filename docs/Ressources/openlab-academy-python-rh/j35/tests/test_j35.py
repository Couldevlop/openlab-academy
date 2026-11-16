"""Journée 35 : la vérification de déploiement ne signale plus rien."""
import importlib
import io
import os
import pathlib

from django.core.management import call_command
from django.test.utils import override_settings


CLEF_DE_TEST = "une-clef-de-test-suffisamment-longue-pour-la-verification"


def reglages_de_production():
    """Rend le module des réglages de mise en service.

    La clé vient de l'environnement et n'a aucune valeur de repli : le test la pose lui-même,
    comme le ferait la machine d'accueil.
    """
    os.environ.setdefault("DJANGO_SECRET_KEY", CLEF_DE_TEST)
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "rh.exemple.ci")
    return importlib.import_module("config.production")


def test_le_module_de_production_existe():
    assert pathlib.Path("config/production.py").is_file()


def test_la_clef_de_production_vient_de_l_environnement():
    source = pathlib.Path("config/production.py").read_text(encoding="utf-8")
    assert 'os.environ["DJANGO_SECRET_KEY"]' in source


def test_aucune_clef_n_est_ecrite_dans_le_depot():
    for chemin in pathlib.Path("config").glob("*.py"):
        texte = chemin.read_text(encoding="utf-8")
        assert "django-insecure" not in texte, chemin


def test_la_verification_de_deploiement_ne_signale_rien():
    production = reglages_de_production()
    reglages = {nom: getattr(production, nom) for nom in dir(production) if nom.isupper()}
    reglages["SECRET_KEY"] = CLEF_DE_TEST
    reglages["ALLOWED_HOSTS"] = ["rh.exemple.ci"]
    sortie = io.StringIO()
    with override_settings(**reglages):
        call_command("check", "--deploy", stdout=sortie, stderr=sortie)
    assert "WARNINGS" not in sortie.getvalue(), sortie.getvalue()


def test_les_hotes_autorises_viennent_de_l_environnement():
    source = pathlib.Path("config/production.py").read_text(encoding="utf-8")
    assert "DJANGO_ALLOWED_HOSTS" in source


def test_les_cookies_ne_voyagent_qu_en_clair_chiffre():
    production = reglages_de_production()
    assert production.SESSION_COOKIE_SECURE is True
    assert production.CSRF_COOKIE_SECURE is True


def test_le_mode_debug_est_eteint_en_production():
    assert reglages_de_production().DEBUG is False


def test_les_pages_de_l_effectif_repondent_toujours(client):
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    agent = get_user_model().objects.create_user("agent", password="mot-de-passe-de-test-1")
    client.force_login(agent)
    assert client.get(reverse("salaries")).status_code == 200
