"""Archives livrées avec l'application, jointes à une leçon en fichier privé.

Un fichier privé de leçon n'est servi que par le contrôle des médias (`entrypoints/lms.py: serve_resource`) : le
parcours doit être ouvert, visible et non bloqué pour le membre, et la leçon accessible. L'archive hérite donc de la
visibilité du parcours sans nouveau point d'entrée.
"""
import hashlib
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


def joindre_couverture(cours: str, nom: str) -> str:
    """Joint l'image de couverture au parcours en fichier public et renvoie son adresse.

    Publique, à l'inverse des archives et des figures : la vignette s'affiche au catalogue, donc avant
    toute inscription. Un parcours n'a qu'une couverture : celle déjà jointe est réutilisée si elle a le
    même contenu, sinon elle est retirée et remplacée. L'appariement se fait sur l'empreinte du contenu,
    jamais sur le nom du fichier — deux parcours peuvent porter le même nom de fichier, et le LMS suffixe
    alors celui qu'il écrit sur disque.

    L'adresse rendue porte l'empreinte du contenu : une couverture redessinée garde son nom de fichier, et
    sans ce marqueur les navigateurs continueraient d'afficher l'ancienne image, gardée en cache.
    """
    contenu = chemin(nom).read_bytes()
    empreinte = hashlib.md5(contenu).hexdigest()
    for deja in frappe.get_all("File", {"attached_to_doctype": "LMS Course", "attached_to_name": cours,
                                        "attached_to_field": "image"}, ["name", "content_hash", "file_url"]):
        if deja.content_hash == empreinte:
            return _datee(deja.file_url, empreinte)
        frappe.delete_doc("File", deja.name, ignore_permissions=True, delete_permanently=True)
    adresse = frappe.get_doc({
        "doctype": "File", "file_name": nom, "is_private": 0, "decode": False,
        "attached_to_doctype": "LMS Course", "attached_to_name": cours, "attached_to_field": "image",
        "content": contenu,
    }).insert(ignore_permissions=True).file_url
    return _datee(adresse, empreinte)


def _datee(adresse: str, empreinte: str) -> str:
    """Adresse d'image suivie de l'empreinte de son contenu, sans jamais empiler deux marqueurs."""
    return f"{adresse.split('?', 1)[0]}?v={empreinte[:12]}"


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
