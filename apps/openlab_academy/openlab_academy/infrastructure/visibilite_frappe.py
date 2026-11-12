"""Phase de lancement : champs personnalisés (créés par entrypoints/install) et source de la visibilité des parcours."""
import frappe
from frappe.utils import getdate

from openlab_academy.domain.fenetre import Fenetre
from openlab_academy.domain.lancement import PhaseLancement
from openlab_academy.infrastructure import reglages_source_frappe
from openlab_academy.infrastructure.depot_cohortes_frappe import cohorte_fenetre

CHAMP_LIMITE = "acces_limite_cohorte"  # Check sur LMS Course : ouvert seulement aux dates de la cohorte
CHAMP_VIDEO = "video_lecon"  # Attach sur Course Lesson : lien ou fichier vidéo, hors du contenu republié


class SourceVisibiliteFrappe:
    """Port SourceVisibilite sur la base. Chaque lecture est retenue pour la vie de l'instance : l'appelant en crée
    une par requête, si bien que `refuses` lit la phase et les limites une seule fois, et qu'une modification des
    dates ou des réglages s'applique dès la requête suivante."""

    def __init__(self):
        self._phase: PhaseLancement | None = None
        self._limites: frozenset[str] | None = None
        self._fenetres: dict[str, Fenetre | None] = {}
        self._cours: tuple[str, ...] | None = None

    def phase(self) -> PhaseLancement:
        if self._phase is None:
            self._phase = reglages_source_frappe.phase_lancement()
        return self._phase

    def cours_limites(self) -> frozenset[str]:
        if self._limites is None:
            self._limites = frozenset(frappe.get_all("LMS Course", {CHAMP_LIMITE: 1}, pluck="name"))
        return self._limites

    def limite(self, cours: str) -> bool:
        return cours in self.cours_limites()

    def fenetre(self, cours: str) -> Fenetre | None:
        """Dates de la cohorte-fenêtre du parcours (la même que celle du rattachement des inscrits)."""
        if cours not in self._fenetres:
            trouvee = cohorte_fenetre(cours, ("name", "start_date", "end_date"))
            self._fenetres[cours] = (Fenetre(getdate(trouvee.start_date), getdate(trouvee.end_date))
                                     if trouvee and trouvee.start_date and trouvee.end_date else None)
        return self._fenetres[cours]

    def tous_les_cours(self) -> tuple[str, ...]:
        if self._cours is None:
            self._cours = tuple(frappe.get_all("LMS Course", pluck="name"))
        return self._cours

    def cours_limites_publies(self) -> tuple[str, ...]:
        return tuple(frappe.get_all("LMS Course", {CHAMP_LIMITE: 1, "published": 1}, pluck="name"))

    def depublier(self, cours: str) -> None:
        """Retire le parcours du catalogue : la seule écriture, sans date de modification ni crochet de document
        (leçons, inscriptions, progressions et certificats restent intacts)."""
        frappe.db.set_value("LMS Course", cours, "published", 0, update_modified=False)
        frappe.clear_document_cache("LMS Course", cours)
