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

    def relectures(self, exercice: str, cohorte: str) -> list[Relecture]:
        c, r = frappe.qb.DocType(COPIE), frappe.qb.DocType(RELECTURE)
        lignes = (frappe.qb.from_(r).join(c).on(r.copie == c.name)
                  .select(r.name, r.copie, r.relecteur, r.statut, r.echeance, r.rappel)
                  .where((c.exercice == exercice) & (c.cohorte == cohorte))
                  .orderby(r.creation).run(as_dict=True))
        return [_relecture(ligne) for ligne in lignes]

    def relecture(self, relecture_id: str) -> Relecture | None:
        ligne = frappe.db.get_value(RELECTURE, relecture_id, CHAMPS, as_dict=True)
        return _relecture(ligne) if ligne else None

    def verrouiller_relecture(self, relecture_id: str) -> Relecture | None:
        ligne = frappe.db.get_value(RELECTURE, relecture_id, CHAMPS, as_dict=True, for_update=True)
        return _relecture(ligne) if ligne else None

    def relectures_echues(self, maintenant) -> list[Relecture]:
        return [_relecture(ligne) for ligne in frappe.get_all(
            RELECTURE, [["statut", "=", StatutRelecture.A_FAIRE.value], ["echeance", "is", "set"],
                        ["echeance", "<=", maintenant]], CHAMPS, order_by="echeance")]

    def attribuer(self, copie_id: str, relecteur: str, echeance) -> str | None:
        """None si la paire (copie, relecteur) existe déjà (contrainte d'unicité, attribution concurrente)."""
        frappe.db.savepoint(POINT)
        try:
            return frappe.get_doc({"doctype": RELECTURE, "copie": copie_id, "relecteur": relecteur,
                                   "statut": StatutRelecture.A_FAIRE.value, "echeance": echeance}
                                  ).insert(ignore_permissions=True).name
        except frappe.UniqueValidationError:
            frappe.db.rollback(save_point=POINT)
            return None

    def rappeler(self, relecture_id: str, echeance) -> None:
        frappe.db.set_value(RELECTURE, relecture_id, {"rappel": 1, "echeance": echeance})

    def changer_statut_relecture(self, relecture_id: str, statut: StatutRelecture) -> None:
        frappe.db.set_value(RELECTURE, relecture_id, "statut", statut.value)

    def dispenser(self, copie_id: str) -> None:
        frappe.db.set_value(COPIE, copie_id, "relectures_dispensees", 1)
