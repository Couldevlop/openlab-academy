"""Lectures du catalogue limité aux parcours visibles, sur la base : port SourceCatalogue. Rien n'est écrit."""
from collections import defaultdict
from collections.abc import Collection

import frappe
from frappe.utils import getdate

BATCH = "LMS Batch"
COURS = "LMS Course"
INSCRIPTION = "LMS Enrollment"
INSCRIPTION_COHORTE = "LMS Batch Enrollment"
CERTIFICAT = "LMS Certificate"


def _hors(champ: str, exclus: Collection[str]) -> dict:
    return {champ: ["not in", list(exclus)]} if exclus else {}


class CatalogueFrappe:
    def noms_correspondants(self, doctype: str, nom) -> list[str]:
        return frappe.get_all(doctype, filters={"name": nom}, pluck="name", limit_page_length=0)

    def cours_par_cohorte(self, lot: str | None = None) -> dict[str, set[str]]:
        filtres = {"parenttype": BATCH, **({"parent": lot} if lot else {})}
        cours_par_lot = defaultdict(set)
        for ligne in frappe.get_all("Batch Course", filtres, ["parent", "course"], limit_page_length=0):
            cours_par_lot[ligne.parent].add(ligne.course)
        return cours_par_lot

    def derniers_parcours_inscrits(self, membre: str, exclus: Collection[str], limite: int) -> list[str]:
        """Les dernières inscriptions du membre à un parcours non exclu (même ordre que l'accueil du LMS)."""
        return frappe.get_all(INSCRIPTION, {"member": membre, **_hors("course", exclus)},
                              order_by="modified desc", limit=limite, pluck="course")

    def parcours_de_repli(self, exclus: Collection[str], limite: int) -> list[str]:
        """Repli de l'accueil du LMS : parcours à la une, à défaut les plus suivis, parmi les parcours non exclus."""
        for filtres, ordre in (({"featured": 1}, "published_on desc"), ({}, "enrollments desc")):
            if noms := frappe.get_all(COURS, {"published": 1, **filtres, **_hors("name", exclus)},
                                      order_by=ordre, limit=limite, pluck="name"):
                return noms
        return []

    def dernieres_cohortes_inscrites(self, membre: str, exclus: Collection[str], limite: int) -> list[str]:
        return frappe.get_all(INSCRIPTION_COHORTE, {"member": membre, **_hors("batch", exclus)},
                              order_by="creation desc", limit=limite, pluck="batch")

    def cohortes_a_venir(self, exclus: Collection[str], limite: int) -> list[str]:
        return frappe.get_all(BATCH, {"published": 1, "start_date": [">=", getdate()], **_hors("name", exclus)},
                              order_by="start_date asc", limit=limite, pluck="name")

    def categories_hors(self, exclus: Collection[str]) -> frozenset[str]:
        """Catégories des parcours publiés non exclus."""
        return frozenset(frappe.get_all(
            COURS, {"published": 1, "category": ["is", "set"], **_hors("name", exclus)}, pluck="category",
            distinct=True, limit_page_length=0))

    def statistiques_hors(self, exclus: Collection[str]) -> dict[str, int]:
        """Les comptes de la page d'accueil du LMS, sans les parcours exclus."""
        hors_cours = _hors("course", exclus)
        return {
            "courses": frappe.db.count(COURS, {"published": 1, "upcoming": 0, **_hors("name", exclus)}),
            "enrollments": frappe.db.count(INSCRIPTION, hors_cours),
            "completions": frappe.db.count(INSCRIPTION, {"progress": ["like", "%100%"], **hors_cours}),
            "certifications": frappe.db.count(CERTIFICAT, {"published": 1, **hors_cours}),
        }
