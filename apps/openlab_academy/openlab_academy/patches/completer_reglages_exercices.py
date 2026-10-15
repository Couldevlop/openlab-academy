"""Sites existants : renseigne les réglages d'exercices absents avec les valeurs par défaut du domaine."""
import frappe

from openlab_academy.domain.reglages import Reglages

DOCTYPE = "Reglages OpenLab Academy"
CHAMPS = ("questions_par_quiz", "tentatives_max", "score_min", "delai_exercices_minutes")


def execute():
    defauts = Reglages()
    for champ in CHAMPS:
        if not frappe.db.get_single_value(DOCTYPE, champ):
            frappe.db.set_single_value(DOCTYPE, champ, getattr(defauts, champ))
