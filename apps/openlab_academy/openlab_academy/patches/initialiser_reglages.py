"""Sites existants : crée l'écran de réglages avec les valeurs en vigueur."""
from openlab_academy.infrastructure import reglages_source_frappe


def execute():
    reglages_source_frappe.initialiser()
