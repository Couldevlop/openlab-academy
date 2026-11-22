"""Page publique /parcours/<nom> : la fiche d'un parcours, et son formulaire d'inscription.

Le nom vient de l'URL. Il n'est jamais interpolé dans une requête brute (lecture par nom exact) ni dans du
HTML non échappé (le gabarit applique `| e`, l'autoéchappement de Frappe étant désactivé), et un parcours
refusé — caché ou fermé — est traité comme inexistant plutôt que signalé : un visiteur ne doit pas pouvoir
apprendre, par la différence entre deux réponses, qu'un parcours existe et se prépare.

La page **porte son offre**, calculée au serveur : état des inscriptions, prochaine session, prix. Elle est
donc juste pour un robot d'indexation comme pour un navigateur sans JavaScript, et le script qui l'habille
ne fait que l'actualiser et poster l'inscription.
"""
import frappe
from frappe import _

from openlab_academy.application.visibilite import CATALOGUE
from openlab_academy.entrypoints import site_api
from openlab_academy.infrastructure import domaines_frappe
from openlab_academy.www import catalogue_public

no_cache = 1


def _programme(cours: str) -> list:
    """Les blocs du parcours et leurs séances, dans l'ordre. Le titre seul : le contenu est réservé aux
    inscrits, et la façade n'a pas à le livrer."""
    chapitres = frappe.get_all("Chapter Reference", {"parent": cours, "parenttype": "LMS Course"},
                               ["chapter", "idx"], order_by="idx asc", ignore_permissions=True)
    programme = []
    for reference in chapitres:
        titre = frappe.db.get_value("Course Chapter", reference.chapter, "title")
        if not titre:
            continue
        lecons = frappe.get_all("Lesson Reference", {"parent": reference.chapter},
                                ["lesson", "idx"], order_by="idx asc", ignore_permissions=True)
        seances = [frappe.db.get_value("Course Lesson", lecon.lesson, "title") for lecon in lecons]
        programme.append({"titre": titre, "seances": [s for s in seances if s]})
    return programme


def get_context(context) -> None:
    context.no_cache = 1
    context.catalogue = CATALOGUE
    context.lien_parcours = "/parcours"
    nom = frappe.form_dict.get("parcours")
    cours = site_api.parcours_du_catalogue(nom)
    if not cours:
        raise frappe.DoesNotExistError

    fiche = frappe.db.get_value(
        "LMS Course", cours,
        ["title", "short_introduction", "description", "image", "category"], as_dict=True)
    offre = site_api._usage().offre(cours, site_api._apprenant()).en_dict()

    context.parcours = cours
    context.titre = fiche.title or cours
    context.accroche = fiche.short_introduction or ""
    context.image = fiche.image or ""
    context.categorie = fiche.category or ""
    context.programme = _programme(cours)
    context.offre = offre
    context.prix = catalogue_public.montant_lisible(offre.get("montant"))

    famille = domaines_frappe.du_parcours(cours)
    context.domaine_libelle = famille.libelle if famille else ""
    context.domaine_teinte = famille.teinte if famille else ""
    # L'état vient du même calcul que les cartes : une fiche qui dirait « bientôt » là où la carte
    # dit « en préparation » userait la confiance plus sûrement qu'une page absente.
    etat = catalogue_public.etat_de({"upcoming": frappe.db.get_value("LMS Course", cours, "upcoming"),
                                     "offre": offre})
    context.etat = etat
    context.etat_libelle = catalogue_public.libelle_etat(etat)
    context.blocs = len(context.programme)
    context.seances = sum(len(bloc["seances"]) for bloc in context.programme)
    context.connecte = bool(site_api._apprenant())
    context.lien_connexion = "/login?redirect-to=" + frappe.utils.quoted(catalogue_public.lien_de(cours))
    context.metatags = {
        "title": context.titre,
        "description": context.accroche or _("Parcours de l'académie Openlab."),
        "image": context.image,
    }
