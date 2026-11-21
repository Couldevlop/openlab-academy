"""Adaptateurs Frappe de l'inscription depuis le site public.

Rien ici ne décide : les trois classes lisent la base et écrivent les documents que le LMS attend. Les
règles sont dans `domain/inscription_ouverte.py` et `application/inscrire_au_parcours.py`.

Un seul point mérite attention, et c'est l'écriture : créer un `LMS Batch Enrollment` déclenche les
`doc_events` de `entrypoints/paiement`, qui vérifient l'inscription tardive, le tarif, la règle de
cohorte, puis ouvrent le dossier de paiement. On ne contourne donc rien — on passe par la porte, et si
elle refuse, elle refuse ici aussi.
"""
import frappe

from openlab_academy.domain.cohorte import PLACES_FENETRE
from openlab_academy.domain.inscription_ouverte import Candidate
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_dossiers_frappe import TarifsFrappe

PLACES_PAR_DEFAUT = 30  # une cohorte sans `seat_count` n'est pas illimitée : elle est mal renseignée


class CohortesPubliquesFrappe:
    """Les cohortes d'un parcours, vues sous l'angle des inscriptions.

    `seat_count` vaut `PLACES_FENETRE` pour une fenêtre d'accès libre : c'est ainsi que le reste de
    l'application la reconnaît (voir `cohorte_fenetre`), et on s'y range plutôt que d'ajouter un champ.
    """

    def candidates(self, cours: str) -> tuple[Candidate, ...]:
        lots = frappe.get_all("Batch Course", {"course": cours, "parenttype": "LMS Batch"}, pluck="parent")
        if not lots:
            return ()
        cohortes = frappe.get_all(
            "LMS Batch", {"name": ["in", lots]},
            ["name", "title", "start_date", "end_date", "seat_count", "published"],
            order_by="start_date asc", ignore_permissions=True)
        return tuple(self._candidate(c) for c in cohortes if c.start_date and c.end_date)

    @staticmethod
    def _candidate(cohorte) -> Candidate:
        places = int(cohorte.seat_count or PLACES_PAR_DEFAUT)
        return Candidate(
            identifiant=cohorte.name,
            titre=cohorte.title or cohorte.name,
            debut=frappe.utils.getdate(cohorte.start_date),
            fin=frappe.utils.getdate(cohorte.end_date),
            places=places,
            inscrits=frappe.db.count("LMS Batch Enrollment", {"batch": cohorte.name}),
            publiee=bool(cohorte.published),
            libre=places == PLACES_FENETRE)


class InscripteurFrappe:
    def deja_inscrit(self, apprenant: str, cours: str) -> bool:
        return bool(frappe.db.exists("LMS Enrollment", {"member": apprenant, "course": cours}))

    def a_la_cohorte(self, apprenant: str, cohorte: str, cours: str) -> None:
        """L'inscription à la cohorte. Le dossier de paiement naît d'elle, par les `doc_events` — le
        redire ici en créerait deux.

        `ignore_permissions` est volontaire et sans danger : le cas d'usage a déjà établi que ce parcours
        accueille cet apprenant, et les `doc_events` revérifient tout derrière. Sans lui, un apprenant ne
        pourrait pas s'inscrire lui-même, faute de droit d'écriture sur le document.
        """
        frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": cohorte,
                        "member": apprenant}).insert(ignore_permissions=True)

    def au_parcours(self, apprenant: str, cours: str) -> None:
        """L'inscription directe, réservée aux parcours gratuits. `avant_inscription_parcours` la refuse
        pour un parcours payant : c'est elle qui tient la règle, pas nous."""
        frappe.get_doc({"doctype": "LMS Enrollment", "course": cours,
                        "member": apprenant}).insert(ignore_permissions=True)


class TarifsPublicsFrappe:
    """Le prix affiché : celui du paiement en une fois, le plus bas des trois.

    Les trois modes (une fois, deux tranches, mensuel) se choisissent sur la page de paiement, une fois
    l'inscription faite. Les montrer tous les trois sur la façade ferait lire un tableau à qui veut
    seulement savoir si c'est dans ses moyens.
    """

    def __init__(self, tarifs=None):
        self._tarifs = tarifs or TarifsFrappe()

    def montant(self, cours: str) -> int | None:
        tarif = self._tarifs.charger(cours)
        return int(tarif.une_fois) if tarif else None


class ReglagesInscriptionFrappe:
    """Les deux réglages dont le cas d'usage public a besoin, pris là où chacun vit.

    Le délai de retard est un réglage de paiement ; la suspension de la façade est un réglage de
    l'académie, aux côtés de la phase de lancement. Les réunir ici, derrière un seul port, évite au
    cas d'usage de connaître deux écrans — et évite de recopier l'un dans l'autre.
    """

    def __init__(self, reglages):
        self._reglages = reglages

    def inscription_tardive_mois(self) -> int:
        return self._reglages.charger().inscription_tardive_mois

    def inscriptions_suspendues(self) -> bool:
        return reglages_source_frappe.inscriptions_suspendues()
