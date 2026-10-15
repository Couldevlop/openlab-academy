"""Hook Frappe after_install : réglages de la plateforme puis publication des parcours."""
from openlab_academy.entrypoints import seed
from openlab_academy.infrastructure import reglages_frappe


def after_install(commit: bool = True) -> None:
    reglages_frappe.appliquer()
    seed.run(commit=commit)
