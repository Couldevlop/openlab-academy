"""Page publique / : l'accueil de l'académie.

C'est la page que l'on trouve avant de savoir ce qu'on cherche. Elle montre donc des parcours réels, avec
leur état d'inscription réel : une vitrine qui annonce des formations fermées envoie le visiteur ailleurs,
et une qui annonce un chiffre inventé le perd pour de bon.

Tout ce qu'elle affiche est compté, jamais écrit à la main.
"""
import frappe

from openlab_academy.www import catalogue_public

no_cache = 1
PARCOURS_EN_VEDETTE = 6


def get_context(context) -> None:
    context.no_cache = 1
    cours = catalogue_public.parcours_visibles()
    enrichis = catalogue_public.avec_offre(cours)
    for p in enrichis:
        p["prix"] = catalogue_public.montant_lisible(p["offre"].get("montant"))

    # Les parcours ouverts d'abord : c'est ce sur quoi on peut agir aujourd'hui.
    ouverts = [p for p in enrichis if p["offre"]["ouverte"]]
    fermes = [p for p in enrichis if not p["offre"]["ouverte"]]
    context.vedette = (ouverts + fermes)[:PARCOURS_EN_VEDETTE]
    context.ouverts = len(ouverts)
    context.chiffres = catalogue_public.chiffres(cours)
    context.lien_parcours = "/parcours"
    context.metatags = {
        "title": frappe._("Openlab Academy — se former à l’IA et à la data, à Abidjan"),
        "description": frappe._(
            "L’académie d’Openlab : parcours en data science, intelligence artificielle, développement "
            "et cybersécurité. Sessions encadrées, projets évalués, certificat à la clé."),
    }
