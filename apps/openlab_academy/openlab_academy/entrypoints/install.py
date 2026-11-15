"""Hooks Frappe after_install / after_migrate : réglages, rôles, case « Parcours gratuit », publication des
parcours, passage au parcours de lancement et sa cohorte."""
import frappe

from openlab_academy.domain.reglages import TITRE_LANCEMENT
from openlab_academy.entrypoints import cohorte, lancement, seed
from openlab_academy.infrastructure import (reglages_evaluation_frappe, reglages_frappe,
                                            reglages_source_frappe)
from openlab_academy.infrastructure.retouches_frappe import CHAMP as CHAMP_RETOUCHE
from openlab_academy.infrastructure.retouches_frappe import SUIVIS
from openlab_academy.infrastructure.depot_dossiers_frappe import CHAMP_GRATUIT
from openlab_academy.infrastructure.depot_ouvertures_frappe import CHAMP_DELAI
from openlab_academy.infrastructure.visibilite_frappe import CHAMP_LIMITE, CHAMP_VIDEO

ROLE_INTENDANT = "Intendant OpenLab"
PARCOURS = "LMS Course"
DOCTYPE_REGLAGES = reglages_source_frappe.DOCTYPE


def preparer_roles() -> None:
    """Rôle de l'intendant (suivi des paiements), créé s'il manque, et choix du parcours d'un tarif."""
    if not frappe.db.exists("Role", ROLE_INTENDANT):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE_INTENDANT, "desk_access": 1}).insert(
            ignore_permissions=True)
    _choix_des_parcours()


def _choix_des_parcours() -> None:
    """L'intendant saisit les tarifs : le champ « Parcours » cherche dans LMS Course. Droit « select » seul (liste
    des noms dans un champ lien), sans lecture des parcours ; les droits standard sont d'abord recopiés, Frappe
    n'appliquant plus que les droits personnalisés dès qu'il en existe un."""
    from frappe.permissions import setup_custom_perms

    if frappe.db.exists("Custom DocPerm", {"parent": PARCOURS, "role": ROLE_INTENDANT, "permlevel": 0}):
        return
    setup_custom_perms(PARCOURS)
    frappe.get_doc({"doctype": "Custom DocPerm", "parent": PARCOURS, "parenttype": "DocType",
                    "parentfield": "permissions", "role": ROLE_INTENDANT, "permlevel": 0, "select": 1,
                    "read": 0}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=PARCOURS)


ADMINISTRATEUR = "System Manager"
NIVEAU_GRATUIT = 1  # niveau de droits de la case : l'administrateur seul la lit et l'écrit


def preparer_parcours_gratuits() -> None:
    """Case « Parcours gratuit (MOOC) » du formulaire des parcours, en tête de la section des prix, réservée à
    l'administrateur (niveau 1) : ni le créateur du parcours, ni le modérateur, ni l'intendant ne la modifient.
    Propriétés remises à jour sur un site où la case existe déjà."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    from frappe.permissions import setup_custom_perms

    proprietes = {"fieldtype": "Check", "label": "Parcours gratuit (MOOC)", "default": "0",
                  "insert_after": "pricing_section", "permlevel": NIVEAU_GRATUIT,
                  "description": "Aucun paiement : ni tarif, ni échéancier, ni rappel, ni blocage."}
    existant = frappe.db.get_value("Custom Field", {"dt": PARCOURS, "fieldname": CHAMP_GRATUIT})
    if existant:
        champ = frappe.get_doc("Custom Field", existant)
        if any(str(champ.get(k)) != str(v) for k, v in proprietes.items()):
            champ.update(proprietes)
            champ.save(ignore_permissions=True)
    else:
        create_custom_field(PARCOURS, {"fieldname": CHAMP_GRATUIT, **proprietes})
    if not frappe.db.exists("Custom DocPerm", {"parent": PARCOURS, "role": ADMINISTRATEUR,
                                               "permlevel": NIVEAU_GRATUIT}):
        setup_custom_perms(PARCOURS)
        frappe.get_doc({"doctype": "Custom DocPerm", "parent": PARCOURS, "parenttype": "DocType",
                        "parentfield": "permissions", "role": ADMINISTRATEUR, "permlevel": NIVEAU_GRATUIT,
                        "read": 1, "write": 1}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=PARCOURS)


def _champ_personnalise(doctype: str, nom: str, proprietes: dict) -> None:
    """Crée le champ personnalisé, ou remet ses propriétés à jour s'il existe déjà."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    existant = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": nom})
    if existant:
        champ = frappe.get_doc("Custom Field", existant)
        if any(str(champ.get(k)) != str(v) for k, v in proprietes.items()):
            champ.update(proprietes)
            champ.save(ignore_permissions=True)
    else:
        create_custom_field(doctype, {"fieldname": nom, **proprietes})


def preparer_champs_lancement() -> None:
    """Case « Accès limité aux dates de la cohorte » des parcours (niveau administrateur, comme la case gratuite)
    et emplacement vidéo des leçons, hors du contenu republié. Aucune validation du lien ici : le filtrage se fait
    à l'affichage."""
    _champ_personnalise(PARCOURS, CHAMP_LIMITE, {
        "fieldtype": "Check", "label": "Accès limité aux dates de la cohorte", "default": "0",
        "insert_after": CHAMP_GRATUIT, "permlevel": NIVEAU_GRATUIT})
    _champ_personnalise(PARCOURS, CHAMP_DELAI, {
        "fieldtype": "Int", "label": "Délai avant les exercices (minutes)", "default": "0",
        "insert_after": CHAMP_LIMITE, "permlevel": NIVEAU_GRATUIT,
        "description": "Temps d'étude exigé entre l'ouverture d'une leçon de ce parcours et l'accès à ses "
                       "exercices. 0 : appliquer le délai réglé pour la plateforme entière."})
    for doctype in SUIVIS:
        _champ_personnalise(doctype, CHAMP_RETOUCHE, {
            "fieldtype": "Check", "label": "Retouché dans l'application", "default": "0",
            "insert_after": "title",
            "description": "Cochée automatiquement dès qu'une retouche est enregistrée ici : la republication "
                           "du fichier de parcours laisse alors cette pièce telle quelle. Décochez-la pour que "
                           "le fichier reprenne la main à la prochaine publication."})
        frappe.clear_cache(doctype=doctype)
    _champ_personnalise("Course Lesson", CHAMP_VIDEO, {
        "fieldtype": "Attach", "label": "Vidéo de la leçon", "insert_after": "title",
        "description": "Lien YouTube, Vimeo ou fichier vidéo ; affichée en tête de la leçon."})
    frappe.clear_cache(doctype=PARCOURS)
    frappe.clear_cache(doctype="Course Lesson")


def preparer_lancement(commit: bool = True) -> None:
    """Passe le site au parcours de lancement, une seule fois : l'écran de réglages en garde la trace
    (« lancement_initialise ») et le choix de l'administrateur survit ensuite aux migrations."""
    doc = frappe.get_single(DOCTYPE_REGLAGES)
    if doc.lancement_initialise:
        return
    doc.update({"parcours_pilote": TITRE_LANCEMENT, "phase_lancement": 1, "lancement_initialise": 1})
    cours = frappe.db.get_value("LMS Course", {"title": TITRE_LANCEMENT})
    doc.set("parcours_lancement", [{"cours": cours}] if cours else [])
    doc.save(ignore_permissions=True)
    cohorte.ouvrir_pilote(commit=commit)


def after_install(commit: bool = True) -> None:
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    preparer_parcours_gratuits()
    preparer_champs_lancement()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    preparer_lancement(commit=commit)


def after_migrate(commit: bool = True) -> None:
    """Republie les parcours à chaque migration : un YAML modifié arrive en base sans commande manuelle. Le retrait
    des parcours dont la fenêtre est close vient en dernier : la republication les remettait au catalogue."""
    reglages_source_frappe.initialiser()
    reglages_evaluation_frappe.preparer()
    preparer_roles()
    preparer_parcours_gratuits()
    preparer_champs_lancement()
    reglages_frappe.appliquer()
    seed.run(commit=commit)
    preparer_lancement(commit=commit)
    lancement.retirer_parcours_echus(commit=commit)
