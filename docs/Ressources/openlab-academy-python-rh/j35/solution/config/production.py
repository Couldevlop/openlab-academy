"""Les réglages de mise en service : ce que la machine d'accueil ajoute aux réglages de base.

Ils ne sont jamais actifs sur la machine de développement : on les charge avec
DJANGO_SETTINGS_MODULE=config.production, et la clé comme les hôtes viennent de l'environnement.
"""
import os

from config.settings import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = [hote for hote in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if hote]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
