"""Catalogue, accueil, recherche et cohortes du LMS limités aux parcours visibles : un parcours fermé (hors fenêtre) ou
caché (phase de lancement) n'y figure pas, pour l'apprenant comme pour le visiteur. Les agents ne sont jamais filtrés
(appel direct de l'original).

Les listes paginées (catalogue, cohortes) excluent par filtre AVANT la requête du LMS, pour que la pagination et le
total restent exacts : le LMS résout lui-même les onglets « inscrits » et « créés » en une condition sur le nom, que
l'exclusion complète sans perdre la portée « à soi » (`is_self_scoped`, qui lit les clés du filtre du client)."""
from collections import defaultdict
from contextlib import contextmanager

import frappe
from frappe.utils import getdate
from lms import command_palette
from lms.lms import api as lms_api
from lms.lms import utils as lms_utils

from openlab_academy.entrypoints import lms

CLE_EXCLUSION = "openlab_catalogue_exclus"
BATCH = "LMS Batch"
COURS = "LMS Course"


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
    if not exclus:
        return
    actuel = filters.get("name")
    if actuel is None:
        filters["name"] = ["not in", list(exclus)]
    elif isinstance(actuel, list | tuple) and len(actuel) == 2 and actuel[0] == "in":
        filters["name"] = ["in", [n for n in actuel[1] if n not in exclus]]
    else:
        retenus = frappe.get_all(doctype, filters={"name": actuel}, pluck="name", limit_page_length=0)
        filters["name"] = ["in", [n for n in retenus if n not in exclus]]


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
def _cours_refuses() -> frozenset[str]:
    utilisateur = frappe.session.user
    if lms._exempte(utilisateur):
        return frozenset()
    return frozenset(lms._cours_refuses(utilisateur))


def _lots_refuses(cours_refuses: frozenset[str], lot: str | None = None) -> frozenset[str]:
    """Cohortes dont TOUS les parcours sont refusés (une cohorte sans parcours reste visible)."""
    if not cours_refuses:
        return frozenset()
    filtres = {"parenttype": BATCH, **({"parent": lot} if lot else {})}
    cours_par_lot = defaultdict(set)
    for ligne in frappe.get_all("Batch Course", filtres, ["parent", "course"], limit_page_length=0):
        cours_par_lot[ligne.parent].add(ligne.course)
    return frozenset(nom for nom, cours in cours_par_lot.items() if cours <= cours_refuses)


# --- catalogue ------------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_courses(filters: dict = None, start: int = 0, limit_page_length: int | str = None) -> list:
    """Surcharge de lms.lms.utils.get_courses : les parcours refusés sont exclus avant la requête (pagination exacte)."""
    with _excluant(_cours_refuses()):
        return lms_utils.get_courses(filters, start, limit_page_length)


@frappe.whitelist(allow_guest=True)
def get_course_count(filters: dict = None) -> int:
    """Surcharge : le total compte les mêmes parcours que la liste."""
    with _excluant(_cours_refuses()):
        return lms_utils.get_course_count(filters)


# --- accueil ----------------------------------------------------------------------------------------------------
@frappe.whitelist()
def get_my_courses() -> list:
    """Surcharge : mes parcours d'accueil sans les parcours refusés. Si tous sont retirés, le repli du LMS (parcours à la
    une, puis les plus suivis) s'applique, choisi parmi les parcours non refusés."""
    refuses = _cours_refuses()
    resultat = lms_api.get_my_courses()
    gardes = [c for c in resultat if c.get("name") not in refuses]
    if gardes or not resultat:
        return gardes
    for filtres, ordre in (({"featured": 1}, "published_on desc"), ({}, "enrollments desc")):
        filtres = {"published": 1, **filtres, **({"name": ["not in", list(refuses)]} if refuses else {})}
        if noms := frappe.get_all(COURS, filtres, order_by=ordre, limit=3, pluck="name"):
            return [d for n in noms if (d := lms_utils.get_course_details(n))]
    return []


@frappe.whitelist(allow_guest=True)
def get_related_courses(course: str) -> list:
    """Surcharge : les parcours associés refusés sont retirés, et un parcours refusé n'en dévoile aucun."""
    refuses = _cours_refuses()
    if course in refuses:
        return []
    return [c for c in lms_utils.get_related_courses(course) if c.get("name") not in refuses]


# --- cohortes ---------------------------------------------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_batches(filters: dict = None, start: int = 0, order_by: str = "start_date",
                limit_page_length: int | str = None):
    """Surcharge : les cohortes dont tous les parcours sont refusés sont exclues avant la requête."""
    with _excluant(_lots_refuses(_cours_refuses())):
        return lms_utils.get_batches(filters, start, order_by, limit_page_length)


@frappe.whitelist()
def get_my_batches() -> list:
    """Surcharge : mes cohortes sans celles dont tous les parcours sont refusés ; si toutes sont retirées, repli du LMS
    (cohortes à venir) choisi parmi les cohortes non refusées."""
    refuses = _lots_refuses(_cours_refuses())
    resultat = lms_api.get_my_batches()
    gardes = [b for b in resultat if b.get("name") not in refuses]
    if gardes or not resultat:
        return gardes
    filtres = {"published": 1, "start_date": [">=", getdate()]}
    if refuses:
        filtres["name"] = ["not in", list(refuses)]
    noms = frappe.get_all(BATCH, filtres, order_by="start_date asc", limit=4, pluck="name")
    return [d for n in noms if (d := lms_utils.get_batch_details(n))]


@frappe.whitelist(allow_guest=True)
def get_batch_details(batch: str):
    """Surcharge : le détail d'une cohorte dont tous les parcours sont refusés n'est pas servi (comme une cohorte
    inexistante pour le LMS)."""
    if batch in _lots_refuses(_cours_refuses(), batch):
        return {}
    return lms_utils.get_batch_details(batch)


# --- recherche --------------------------------------------------------------------------------------------------
@frappe.whitelist()
def search_sqlite(query: str, category: str | None = None):
    """Surcharge de la palette de commandes : lignes de parcours refusés et de cohortes entièrement refusées retirées,
    groupes devenus vides compris."""
    groupes = command_palette.search_sqlite(query, category)
    refuses = _cours_refuses()
    if not refuses:
        return groupes
    lots = _lots_refuses(refuses)
    exclus = {"LMS Course": refuses, BATCH: lots}
    filtres = []
    for groupe in groupes:
        items = [i for i in groupe["items"] if i.get("name") not in exclus.get(i.get("doctype"), ())]
        if items:
            filtres.append({**groupe, "items": items})
    return filtres
