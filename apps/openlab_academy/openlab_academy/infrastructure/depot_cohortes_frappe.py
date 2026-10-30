"""Adaptateur de sortie : cohortes du domaine -> doctype LMS Batch."""
import frappe

from openlab_academy.domain.cohorte import PLACES_FENETRE, Cohorte


def cohorte_fenetre(cours: str, champs: tuple[str, ...] = ("name",)):
    """Cohorte-fenêtre d'un parcours : la cohorte publiée à accès libre (places de la fenêtre, jamais celles d'une
    cohorte pilote) qui le porte, la plus récente si plusieurs. Seule sélection, partagée par le rattachement des
    inscrits et les dates de visibilité."""
    lots = frappe.get_all("Batch Course", {"course": cours, "parenttype": "LMS Batch"}, pluck="parent")
    if not lots:
        return None
    trouvees = frappe.get_all("LMS Batch", {"name": ["in", lots], "published": 1, "seat_count": PLACES_FENETRE},
                              list(champs), order_by="start_date desc", limit=1)
    return trouvees[0] if trouvees else None


class DepotCohortesFrappe:
    def __init__(self, formateur: str = "Administrator"):
        self._formateur = formateur

    def trouver(self, titre: str) -> str | None:
        return frappe.db.get_value("LMS Batch", {"title": titre})

    def fenetre_de(self, cours: str) -> str | None:
        """Cohorte-fenêtre du parcours (voir `cohorte_fenetre`)."""
        trouvee = cohorte_fenetre(cours)
        return trouvee.name if trouvee else None

    def creer(self, cohorte: Cohorte) -> str:
        cours = frappe.db.get_value("LMS Course", {"title": cohorte.cours})
        if not cours:
            raise ValueError(f"cours « {cohorte.cours} » introuvable : publiez les parcours d'abord")
        if cohorte.rythme is None:
            description = "Parcours en vidéo, à votre rythme : quiz, exercices et projet final corrigé sur la plateforme."
            details = f"<p>Ouvert du {cohorte.debut:%d/%m/%Y} au {cohorte.fin:%d/%m/%Y} inclus, à toute heure.</p>"
        else:
            description = "Cohorte pilote en soirée : modules hebdomadaires, semaines projet, capstone devant jury."
            details = (f"<p><b>Format {cohorte.rythme.libelle.lower()}</b> — {cohorte.rythme.descriptif}.</p>"
                       f"<p>{cohorte.seances}</p>")
        return frappe.get_doc({
            "doctype": "LMS Batch", "title": cohorte.titre, "published": 1, "medium": "Online",
            "start_date": cohorte.debut, "end_date": cohorte.fin,
            "start_time": cohorte.heure_debut, "end_time": cohorte.heure_fin, "timezone": cohorte.fuseau,
            "description": description, "batch_details": details,
            "instructors": [{"instructor": self._formateur}], "courses": [{"course": cours}],
            "allow_self_enrollment": 1, "seat_count": cohorte.places, "certification": 1, "evaluation": 1,
        }).insert(ignore_permissions=True).name
