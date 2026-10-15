"""Hook Frappe after_install : réglages, publication des parcours, ouverture de la cohorte pilote."""
from openlab_academy.entrypoints import cohorte, seed
from openlab_academy.infrastructure import reglages_frappe


def after_install(commit: bool = True) -> None:
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    cohorte.ouvrir_pilote(commit=commit)
