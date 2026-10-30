"""Catalogue, accueil, recherche et cohortes du LMS limités aux parcours visibles : un parcours fermé (hors fenêtre) ou
caché (phase de lancement) n'y figure pas, pour l'apprenant comme pour le visiteur. Les agents ne sont jamais filtrés
(appel direct de l'original).

Les listes paginées (catalogue, cohortes) excluent par filtre AVANT la requête du LMS, pour que la pagination et le
total restent exacts : le LMS résout lui-même les onglets « inscrits » et « créés » en une condition sur le nom, que
l'exclusion complète sans perdre la portée « à soi » (`is_self_scoped`, qui lit les clés du filtre du client)."""
from contextlib import contextmanager

import frappe
from lms import command_palette
from lms.lms import api as lms_api
from lms.lms import utils as lms_utils

from openlab_academy.application import catalogue as regles
from openlab_academy.entrypoints import lms
from openlab_academy.infrastructure.catalogue_frappe import BATCH, COURS, CatalogueFrappe

CLE_EXCLUSION = "openlab_catalogue_exclus"
TITRE_FILET = "Catalogue : parcours refusé servi par le LMS"
ACCUEIL_PARCOURS = 3  # comme l'accueil du LMS
ACCUEIL_COHORTES = 4


# --- exclusion posée pour la durée d'un appel (locale à la requête) ---------------------------------------------
@contextmanager
def _excluant(noms):
    precedent = getattr(frappe.local, CLE_EXCLUSION, None)
    setattr(frappe.local, CLE_EXCLUSION, tuple(noms) or None)
    try:
        yield
    finally:
        setattr(frappe.local, CLE_EXCLUSION, precedent)


def _exclure(filters: dict, exclus, doctype: str) -> None:
    """Ajoute `name not in exclus` au filtre, en place. Un filtre de nom déjà posé (onglet « inscrits » ou « créés »,
    ou nom du client) est conservé et amputé des exclus."""
    if exclus:
        filters["name"] = regles.filtre_de_nom(filters.get("name"), exclus, CatalogueFrappe(), doctype)


def _poser_exclusion_sur_les_parcours(original):
    def update_course_filters(filters: dict) -> tuple:
        resultat = original(filters)
        _exclure(resultat[0], getattr(frappe.local, CLE_EXCLUSION, None), COURS)
        return resultat
    update_course_filters.original = original
    return update_course_filters


def _poser_exclusion_sur_les_cohortes(original):
    def update_batch_filters(filters: dict) -> None:
        original(filters)
        _exclure(filters, getattr(frappe.local, CLE_EXCLUSION, None), BATCH)
    update_batch_filters.original = original
    return update_batch_filters


# Le LMS résout « inscrits » / « créés » dans ces deux fonctions, appelées par son propre module : l'exclusion s'y
# glisse (sans effet hors de nos surcharges, `CLE_EXCLUSION` étant alors vide). Posé une seule fois à l'import.
if not hasattr(lms_utils.update_course_filters, "original"):
    lms_utils.update_course_filters = _poser_exclusion_sur_les_parcours(lms_utils.update_course_filters)
if not hasattr(lms_utils.update_batch_filters, "original"):
    lms_utils.update_batch_filters = _poser_exclusion_sur_les_cohortes(lms_utils.update_batch_filters)


# --- ce qui est refusé à l'utilisateur courant ------------------------------------------------------------------
def _lots_refuses(cours_refuses: frozenset[str], lot: str | None = None) -> frozenset[str]:
    """Cohortes dont TOUS les parcours sont refusés (une cohorte sans parcours reste visible)."""
    if not cours_refuses:
        return frozenset()
    return regles.lots_entierement_refuses(CatalogueFrappe().cours_par_cohorte(lot), cours_refuses)


def _filet(lignes: list, exclus: frozenset[str]) -> list:
    """Défense en profondeur : si le LMS cesse d'appeler les fonctions de filtre, l'exclusion avant requête tombe
    sans erreur ; la liste servie est donc refiltrée, et l'anomalie journalisée. Sans effet dans le cas normal."""
    if not exclus:
        return lignes
    gardees = regles.sans_les_exclus(lignes, exclus)
    if len(gardees) != len(lignes):
        frappe.log_error(title=TITRE_FILET, message=f"{len(lignes) - len(gardees)} ligne(s) retirée(s)")
    return gardees


# --- catalogue ------------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_courses(filters: dict = None, start: int = 0, limit_page_length: int | str = None) -> list:
    """Surcharge de lms.lms.utils.get_courses : les parcours refusés sont exclus avant la requête (pagination exacte),
    puis la liste est refiltrée par précaution."""
    refuses = lms.cours_refuses_courants()
    with _excluant(refuses):
        return _filet(lms_utils.get_courses(filters, start, limit_page_length), refuses)


@frappe.whitelist(allow_guest=True)
def get_course_count(filters: dict = None) -> int:
    """Surcharge : le total compte les mêmes parcours que la liste."""
    with _excluant(lms.cours_refuses_courants()):
        return lms_utils.get_course_count(filters)


@frappe.whitelist(allow_guest=True)
def get_course_categories() -> list:
    """Surcharge : les catégories des seuls parcours non refusés (l'option vide du LMS est conservée)."""
    options = lms_utils.get_course_categories()
    if not (refuses := lms.cours_refuses_courants()):
        return options
    visibles = CatalogueFrappe().categories_hors(refuses)
    return [o for o in options if o.get("value") is None or o.get("value") in visibles]


@frappe.whitelist(allow_guest=True)
def get_chart_details():
    """Surcharge : les comptes de l'accueil (parcours, inscriptions, achèvements, certificats) sans les parcours
    refusés."""
    details = lms_api.get_chart_details()
    if refuses := lms.cours_refuses_courants():
        details.update(CatalogueFrappe().statistiques_hors(refuses))
    return details


@frappe.whitelist(allow_guest=True)
def get_reviews(course: str):
    """Surcharge : les avis d'un parcours fermé ou caché ne sont pas servis (visiteur compris)."""
    lms.refuser_visibilite(course)
    return lms_utils.get_reviews(course)


@frappe.whitelist()
def get_order_summary(doctype: str, docname: str, coupon: str | None = None, country: str | None = None):
    """Surcharge : le titre et le prix d'un parcours fermé ou caché ne sont pas servis."""
    if doctype == COURS:
        lms.refuser_visibilite(docname)
    return lms_utils.get_order_summary(doctype, docname, coupon, country)


@frappe.whitelist()
def get_program_details(program_name: str) -> dict:
    """Surcharge : les parcours refusés sont retirés de la fiche d'un programme."""
    programme = lms_utils.get_program_details(program_name)
    if (refuses := lms.cours_refuses_courants()) and programme.get("courses"):
        programme["courses"] = regles.sans_les_exclus(programme["courses"], refuses)
    return programme


# --- accueil ----------------------------------------------------------------------------------------------------
@frappe.whitelist()
def get_my_courses() -> list:
    """Surcharge : mes parcours d'accueil sans les parcours refusés. Les trois dernières inscriptions VISIBLES sont
    servies ; sans aucune, le repli du LMS (parcours à la une, puis les plus suivis) est choisi parmi les non refusés."""
    if not (refuses := lms.cours_refuses_courants()):
        return lms_api.get_my_courses()
    source = CatalogueFrappe()
    noms = (source.derniers_parcours_inscrits(frappe.session.user, refuses, ACCUEIL_PARCOURS)
            or source.parcours_de_repli(refuses, ACCUEIL_PARCOURS))
    return [d for n in noms if (d := lms_utils.get_course_details(n))]


@frappe.whitelist(allow_guest=True)
def get_related_courses(course: str) -> list:
    """Surcharge : les parcours associés refusés sont retirés, et un parcours refusé n'en dévoile aucun."""
    refuses = lms.cours_refuses_courants()
    if course in refuses:
        return []
    return regles.sans_les_exclus(lms_utils.get_related_courses(course), refuses)


# --- cohortes ---------------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_batches(filters: dict = None, start: int = 0, order_by: str = "start_date",
                limit_page_length: int | str = None):
    """Surcharge : les cohortes dont tous les parcours sont refusés sont exclues avant la requête, puis la liste est
    refiltrée par précaution."""
    lots = _lots_refuses(lms.cours_refuses_courants())
    with _excluant(lots):
        return _filet(lms_utils.get_batches(filters, start, order_by, limit_page_length), lots)


@frappe.whitelist(allow_guest=True)
def get_batch_count(filters: dict = None) -> int:
    """Surcharge : le total compte les mêmes cohortes que la liste."""
    with _excluant(_lots_refuses(lms.cours_refuses_courants())):
        return lms_utils.get_batch_count(filters)


@frappe.whitelist()
def get_my_batches() -> list:
    """Surcharge : mes cohortes sans celles dont tous les parcours sont refusés. Les quatre dernières inscriptions
    VISIBLES sont servies ; sans aucune, repli du LMS (cohortes à venir) choisi parmi les cohortes non refusées."""
    refuses = lms.cours_refuses_courants()
    if not refuses:
        return lms_api.get_my_batches()
    lots = _lots_refuses(refuses)
    source = CatalogueFrappe()
    noms = (source.dernieres_cohortes_inscrites(frappe.session.user, lots, ACCUEIL_COHORTES)
            or source.cohortes_a_venir(lots, ACCUEIL_COHORTES))
    return [d for n in noms if (d := _details_de_cohorte(n, refuses))]


def _details_de_cohorte(lot: str, refuses: frozenset[str]) -> dict:
    """Détail d'une cohorte sans les parcours refusés (un titre de parcours caché ne fuit pas)."""
    details = lms_utils.get_batch_details(lot)
    if refuses and details and details.get("courses"):
        details["courses"] = regles.sans_les_exclus(details["courses"], refuses, "course")
    return details


@frappe.whitelist(allow_guest=True)
def get_batch_details(batch: str):
    """Surcharge : le détail d'une cohorte dont tous les parcours sont refusés n'est pas servi (comme une cohorte
    inexistante pour le LMS) ; une cohorte mixte ne nomme pas ses parcours refusés."""
    refuses = lms.cours_refuses_courants()
    if batch in _lots_refuses(refuses, batch):
        return {}
    return _details_de_cohorte(batch, refuses)


@frappe.whitelist(allow_guest=True)
def get_batch_courses(batch: str) -> list:
    """Surcharge : les fiches des parcours refusés sont retirées ; une cohorte entièrement refusée n'en montre aucune."""
    refuses = lms.cours_refuses_courants()
    if batch in _lots_refuses(refuses, batch):
        return []
    return regles.sans_les_exclus(lms_utils.get_batch_courses(batch), refuses)


# --- recherche --------------------------------------------------------------------------------------------------
@frappe.whitelist()
def search_sqlite(query: str, category: str | None = None):
    """Surcharge de la palette de commandes : lignes de parcours refusés et de cohortes entièrement refusées retirées,
    groupes devenus vides compris."""
    groupes = command_palette.search_sqlite(query, category)
    refuses = lms.cours_refuses_courants()
    if not refuses:
        return groupes
    exclus = {"LMS Course": refuses, BATCH: _lots_refuses(refuses)}
    filtres = []
    for groupe in groupes:
        items = [i for i in groupe["items"] if i.get("name") not in exclus.get(i.get("doctype"), ())]
        if items:
            filtres.append({**groupe, "items": items})
    return filtres
