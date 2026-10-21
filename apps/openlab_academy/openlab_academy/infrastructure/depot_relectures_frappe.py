"""Adaptateur : relectures entre pairs (Relecture Pair OpenLab) et vivier de la cohorte dans Frappe."""
import frappe
from frappe.utils import get_datetime

from openlab_academy.application.pairs import Relecture, StatutRelecture
from openlab_academy.domain.copie import Copie
from openlab_academy.infrastructure.depot_copies_frappe import COPIE, RELECTURE, _copie

CHAMPS = ["name", "copie", "relecteur", "statut", "echeance", "rappel"]
POINT = "openlab_attribution"


def _relecture(ligne) -> Relecture:
    return Relecture(ligne.name, ligne.copie, ligne.relecteur, StatutRelecture(ligne.statut),
                     get_datetime(ligne.echeance) if ligne.echeance else None, bool(ligne.rappel))


class DepotRelecturesFrappe:
    def copies_rendues(self, exercice: str, cohorte: str) -> list[Copie]:
        """Version courante de chaque apprenant, hors copies renvoyées, dans l'ordre des rendus."""
        lignes = frappe.get_all(COPIE, {"exercice": exercice, "cohorte": cohorte, "statut": ["!=", "renvoyee"]},
                                ["name", "apprenant", "exercice", "cohorte", "type_exercice", "version", "statut",
                                 "creation"], order_by="version desc, creation desc")
        courantes = {}
        for ligne in lignes:
            courantes.setdefault(ligne.apprenant, ligne)
        return [_copie(ligne) for ligne in sorted(courantes.values(), key=lambda ligne: ligne.creation)]

    def taille_cohorte(self, cohorte: str) -> int:
        return frappe.db.count("LMS Batch Enrollment", {"batch": cohorte}) if cohorte else 0

    def relectures(self, exercice: str, cohorte: str, verrouillee: bool = False) -> list[Relecture]:
        """Verrouillée : lecture à jour, qui voit une relecture rendue par une autre transaction."""
        c, r = frappe.qb.DocType(COPIE), frappe.qb.DocType(RELECTURE)
        requete = (frappe.qb.from_(r).join(c).on(r.copie == c.name)
                   .select(r.name, r.copie, r.relecteur, r.statut, r.echeance, r.rappel)
                   .where((c.exercice == exercice) & (c.cohorte == cohorte))
                   .orderby(r.creation))
        if verrouillee:
            requete = requete.for_update()
        return [_relecture(ligne) for ligne in requete.run(as_dict=True)]

    def relecture(self, relecture_id: str) -> Relecture | None:
        ligne = frappe.db.get_value(RELECTURE, relecture_id, CHAMPS, as_dict=True)
        return _relecture(ligne) if ligne else None

    def verrouiller_relecture(self, relecture_id: str) -> Relecture | None:
        ligne = frappe.db.get_value(RELECTURE, relecture_id, CHAMPS, as_dict=True, for_update=True)
        return _relecture(ligne) if ligne else None

    def relectures_copie(self, copie_id: str) -> list[Relecture]:
        """Lecture verrouillante : les relectures validées par d'autres transactions sont vues."""
        return [_relecture(ligne) for ligne in frappe.db.get_values(
            RELECTURE, {"copie": copie_id}, CHAMPS, as_dict=True, order_by="creation", for_update=True)]

    def relectures_du_relecteur(self, relecteur: str) -> list[Relecture]:
        return [_relecture(ligne) for ligne in frappe.get_all(RELECTURE, {"relecteur": relecteur}, CHAMPS,
                                                              order_by="creation")]

    def relectures_echues(self, maintenant) -> list[Relecture]:
        return [_relecture(ligne) for ligne in frappe.get_all(
            RELECTURE, [["statut", "=", StatutRelecture.A_FAIRE.value], ["echeance", "is", "set"],
                        ["echeance", "<=", maintenant]], CHAMPS, order_by="echeance")]

    def attribuer(self, copie_id: str, relecteur: str, echeance) -> str | None:
        """None si la paire (copie, relecteur) existe déjà (contrainte d'unicité, attribution concurrente)."""
        if frappe.db.exists(RELECTURE, {"copie": copie_id, "relecteur": relecteur}):
            return None
        messages = len(frappe.local.message_log)
        frappe.db.savepoint(POINT)
        try:
            return frappe.get_doc({"doctype": RELECTURE, "copie": copie_id, "relecteur": relecteur,
                                   "statut": StatutRelecture.A_FAIRE.value, "echeance": echeance}
                                  ).insert(ignore_permissions=True).name
        except frappe.UniqueValidationError:  # insérée entre-temps par une transaction concurrente
            frappe.db.rollback(save_point=POINT)
            del frappe.local.message_log[messages:]  # retire le seul message d'unicité, pas les autres
            return None

    def rappeler(self, relecture_id: str, echeance) -> None:
        frappe.db.set_value(RELECTURE, relecture_id, {"rappel": 1, "echeance": echeance})

    def changer_statut_relecture(self, relecture_id: str, statut: StatutRelecture) -> None:
        frappe.db.set_value(RELECTURE, relecture_id, "statut", statut.value)

    def dispenser(self, copie_id: str) -> None:
        frappe.db.set_value(COPIE, copie_id, "relectures_dispensees", 1)
