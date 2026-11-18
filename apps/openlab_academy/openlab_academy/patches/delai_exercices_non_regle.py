"""Sites existants : le zéro des parcours devient -1.

Le champ « Délai avant les exercices » d'un parcours lisait 0 comme « rien de réglé ici, prendre le délai de
la plateforme ». Un parcours peut désormais exiger l'ouverture immédiate de ses exercices, et le dit avec 0 ;
l'absence de consigne s'écrit -1. Les parcours déjà publiés portent un 0 qui voulait dire « absence » : il est
traduit, sans quoi leurs exercices s'ouvriraient d'un coup.
"""
import frappe

from openlab_academy.infrastructure.depot_ouvertures_frappe import CHAMP_DELAI

PARCOURS = "LMS Course"


def execute():
    if not frappe.db.has_column(PARCOURS, CHAMP_DELAI):
        return
    frappe.db.sql(f"update `tab{PARCOURS}` set `{CHAMP_DELAI}` = -1 where coalesce(`{CHAMP_DELAI}`, 0) = 0")
    frappe.clear_cache(doctype=PARCOURS)
