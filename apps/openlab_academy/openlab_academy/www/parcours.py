"""Page publique /parcours : le catalogue, avec l'état des inscriptions de chacun.

Rendue par le serveur, parce qu'elle est la page que l'on cherche : c'est elle qui doit être trouvée, et
elle doit être juste à la seconde où on l'ouvre — une place restante affichée de travers se paie en
inscription refusée.
"""
import frappe

from openlab_academy.www import catalogue_public

no_cache = 1


def get_context(context) -> None:
    context.no_cache = 1
    cours = catalogue_public.parcours_visibles()
    context.parcours = catalogue_public.pour_les_cartes(catalogue_public.avec_offre(cours))
    context.ouverts = sum(1 for p in context.parcours if p["offre"]["ouverte"])
    context.familles = catalogue_public.familles_du_catalogue(context.parcours)
    context.metatags = {
        "title": frappe._("Les parcours — Openlab Academy"),
        # Un seul littéral : voir la note de www/accueil.py — deux littéraux accolés donnent une clé
        # de traduction tronquée, que l'extracteur voit mais que le programme n'emploie jamais.
        "description": frappe._("Parcours de l'académie Openlab : data science, intelligence artificielle, développement, cybersécurité. Formations en ligne, à Abidjan."),  # noqa: E501
    }
