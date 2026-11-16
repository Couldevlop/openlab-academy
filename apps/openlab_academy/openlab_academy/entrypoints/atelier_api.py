"""API de l'atelier de code : les fichiers du dépôt du jour, pour la leçon ouverte.

L'atelier exécute Python dans le navigateur de l'apprenant ; le serveur ne fait que remettre les
fichiers du dépôt déjà joint à la leçon. Rien de ce que l'apprenant écrit ne revient ici : aucune
écriture, aucune exécution côté serveur, donc aucune surface d'exécution ajoutée (OWASP A03).

L'accès est décidé par la leçon, comme pour l'archive elle-même : parcours ni caché ni bloqué pour
ce membre, et leçon accessible (OWASP A01). Le nom de l'archive n'est jamais pris du client : il
vient du fichier joint à la leçon, et il est relu dans le dossier des ressources de l'application.
"""
import zipfile

import frappe
from frappe import _
from lms.lms.permissions import can_access_lesson

from openlab_academy.entrypoints import lms as controle
from openlab_academy.infrastructure import ressources_frappe

# au-delà, un fichier n'est pas du code à éditer : l'atelier ne le propose pas
TAILLE_MAX = 200_000
# dossiers de l'archive : le corrigé de la veille n'est pas ouvert dans l'atelier, il se lit à part
IGNORES = ("corrige/",)
EXTENSIONS = (".py", ".md", ".txt", ".csv", ".cfg", ".toml", ".json")


def _lecon_ouverte(lecon: str) -> str:
    """Rend le parcours de la leçon si elle est accessible au membre, sinon refuse."""
    cours = frappe.db.get_value("Course Lesson", lecon, "course")
    if not cours:
        frappe.throw(_("Leçon introuvable"), frappe.DoesNotExistError)
    utilisateur = frappe.session.user
    if controle.refus_pour(utilisateur, cours) or controle.bloque_pour(utilisateur, cours):
        raise frappe.PermissionError
    if not can_access_lesson(lecon):
        raise frappe.PermissionError
    return cours


def _archive_de(lecon: str) -> str:
    """Nom de l'archive jointe à la leçon. Jamais une valeur venue du client."""
    noms = frappe.get_all("File", filters={"attached_to_doctype": "Course Lesson",
                                           "attached_to_name": lecon,
                                           "file_name": ["like", "%.zip"]}, pluck="file_name")
    if not noms:
        frappe.throw(_("Cette leçon n'a pas de dépôt du jour."), frappe.DoesNotExistError)
    return noms[0]


def _fichiers(archive: str) -> list[dict[str, str]]:
    """Fichiers texte du dépôt, hors corrigé, triés, prêts à être ouverts dans l'atelier."""
    sortie = []
    with zipfile.ZipFile(ressources_frappe.chemin(archive)) as zip_:
        for info in sorted(zip_.infolist(), key=lambda i: i.filename):
            nom = info.filename
            if (info.is_dir() or nom.startswith(IGNORES) or info.file_size > TAILLE_MAX
                    or not nom.endswith(EXTENSIONS)):
                continue
            sortie.append({"nom": nom, "contenu": zip_.read(nom).decode("utf-8")})
    return sortie


@frappe.whitelist()
def ouvrir(lecon: str) -> dict:
    """Rend de quoi garnir l'atelier : titre de la leçon, nom du dépôt et fichiers à éditer."""
    _lecon_ouverte(lecon)
    archive = _archive_de(lecon)
    return {"lecon": lecon,
            "titre": frappe.db.get_value("Course Lesson", lecon, "title") or lecon,
            "archive": archive,
            "fichiers": _fichiers(archive)}
