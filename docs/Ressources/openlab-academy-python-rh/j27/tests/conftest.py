"""Montage de Django pour les tests, sans plugin : une base de test par session.

Chaque test tourne dans une transaction annulée à la fin, pour qu'un test ne laisse jamais de
données derrière lui.
"""
import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402  (l'import doit suivre le réglage de la variable d'environnement)

django.setup()

from django.db import connection, transaction  # noqa: E402
from django.test.utils import setup_test_environment, teardown_test_environment  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def base_de_test():
    """Crée une base vide pour la session de tests, puis la supprime."""
    setup_test_environment()
    reglages = connection.creation.create_test_db(verbosity=0, autoclobber=True)
    yield
    connection.creation.destroy_test_db(reglages, verbosity=0)
    teardown_test_environment()


@pytest.fixture(autouse=True)
def transaction_annulee(base_de_test):
    """Isole chaque test : tout ce qu'il écrit est annulé à la fin."""
    atomique = transaction.atomic()
    atomique.__enter__()
    yield
    transaction.set_rollback(True)
    atomique.__exit__(None, None, None)


@pytest.fixture()
def client():
    """Un client HTTP de test, anonyme."""
    from django.test import Client
    return Client()
