"""Hooks Frappe after_install / after_migrate : réglages, publication des parcours, cohorte pilote."""
from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_evaluation_frappe, reglages_frappe, reglages_source_frappe


def after_install(commit: bool = True) -> None:
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    cohorte.ouvrir_pilote(commit=commit)


def after_migrate(commit: bool = True) -> None:
    """Republie les parcours à chaque migration : un YAML modifié arrive en base sans commande manuelle."""
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    seed.run(commit=commit)
