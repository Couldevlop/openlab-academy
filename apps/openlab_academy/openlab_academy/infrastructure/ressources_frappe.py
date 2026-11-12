"""Archives livrées avec l'application, jointes à une leçon en fichier privé.

Un fichier privé de leçon n'est servi que par le contrôle des médias (`entrypoints/lms.py: serve_resource`) : le
parcours doit être ouvert, visible et non bloqué pour le membre, et la leçon accessible. L'archive hérite donc de la
visibilité du parcours sans nouveau point d'entrée.
"""
import pathlib

import frappe

DOSSIER = pathlib.Path(__file__).resolve().parents[1] / "data" / "ressources"
# champ cité : le LMS réserve un fichier à l'équipe quand le champ est vide ou réservé aux instructeurs
CHAMP = "content"


class RessourceInconnue(FileNotFoundError):
    """L'archive demandée n'est pas livrée avec l'application."""


def chemin(nom: str) -> pathlib.Path:
    """Chemin de l'archive livrée. Le nom vient du fichier de parcours, déjà refusé s'il n'est pas un nom de fichier
    seul ; la sortie du dossier est vérifiée ici aussi (OWASP A01, deux barrières)."""
    dossier = DOSSIER.resolve()
    fichier = (dossier / nom).resolve()
    if fichier.parent != dossier or not fichier.is_file():
        raise RessourceInconnue(f"archive absente des ressources de l'application : {nom}")
    return fichier


def joindre(lecon: str, nom: str) -> str:
    """Joint l'archive à la leçon en fichier privé et renvoie son adresse ; une archive déjà jointe est réutilisée."""
    deja = frappe.db.get_value("File", {"attached_to_doctype": "Course Lesson", "attached_to_name": lecon,
                                        "file_name": nom, "is_private": 1}, "file_url")
    if deja:
        return deja
    fichier = chemin(nom)
    return frappe.get_doc({
        "doctype": "File", "file_name": nom, "is_private": 1, "decode": False,
        "attached_to_doctype": "Course Lesson", "attached_to_name": lecon, "attached_to_field": CHAMP,
        "content": fichier.read_bytes(),
    }).insert(ignore_permissions=True).file_url
