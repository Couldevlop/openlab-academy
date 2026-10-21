"""Sites existants : une version déjà supplantée par un nouveau rendu (sortie de la chaîne) devient « remplacée »."""
from openlab_academy.infrastructure import depot_copies_frappe


def execute():
    depot_copies_frappe.marquer_versions_remplacees()
