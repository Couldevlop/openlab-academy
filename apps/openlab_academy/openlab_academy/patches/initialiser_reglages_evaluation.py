"""Sites existants : crée la console de l'évaluation (réglages par défaut, rôle, espace de travail)."""
from openlab_academy.infrastructure import reglages_evaluation_frappe


def execute():
    reglages_evaluation_frappe.preparer()
