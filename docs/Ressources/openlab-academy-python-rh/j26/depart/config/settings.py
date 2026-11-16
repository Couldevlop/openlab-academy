"""Réglages du projet RH.

Trois choses sont à corriger ici : l'application effectif n'est pas déclarée, la clé est écrite
en dur, et le mode debug est allumé quoi qu'il arrive.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-ne-laissez-jamais-une-clef-dans-le-code"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": BASE_DIR / "effectif.sqlite3"}}

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
