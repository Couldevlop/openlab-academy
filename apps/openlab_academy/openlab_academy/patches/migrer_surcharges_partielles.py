"""Sites existants : surcharges devenues partielles, suppléants déplacés dans les équipes de correction."""
from openlab_academy.infrastructure import reglages_evaluation_frappe


def execute():
    reglages_evaluation_frappe.migrer_surcharges_partielles()
