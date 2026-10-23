"""Sites existants : la case « inscription autonome désactivée » du LMS est cochée sur chaque parcours payant (le
bouton « Enroll Now » y cède la place à « contactez l'administrateur ») ; les parcours gratuits ne changent pas."""
import frappe

from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT


def execute():
    filtres = {"disable_self_learning": 0}
    if frappe.db.has_column("LMS Course", CHAMP_GRATUIT):
        filtres[CHAMP_GRATUIT] = 0
    for cours in frappe.get_all("LMS Course", filtres, pluck="name"):
        frappe.db.set_value("LMS Course", cours, "disable_self_learning", 1, update_modified=False)
