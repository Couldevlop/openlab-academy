"""Les parties d'une séance : chaque rubrique dans son propre éditeur, modifiable sans republier le parcours.

Une séance reste une leçon pour l'apprenant, mais elle s'écrit partie par partie. La publication dépose une
`Partie Lecon OpenLab` par rubrique, déjà remplie, puis assemble la leçon depuis ces parties. L'administrateur
ouvre une partie, la retouche dans l'éditeur riche, enregistre : la leçon est réassemblée aussitôt et les
autres parties ne bougent pas.

Deux représentations, pour ne jamais abîmer ce que le fichier a écrit :

- `blocs`, les blocs EditorJS venus du fichier de parcours, en lecture seule ; ils servent tant que la partie
  n'a pas été retouchée, et gardent la fidélité exacte du rendu (langage d'un extrait, légende d'une figure,
  en-têtes d'un tableau, blocs d'exercice) ;
- `contenu`, le HTML de l'éditeur, qui prend la main dès que la partie porte sa case de retouche.

La republication détruit puis recrée les leçons : une partie retouchée se retrouve par (titre de la leçon,
clé de la rubrique), et les identifiants d'exercices qu'elle cite sont remplacés par les nouveaux, comme pour
une leçon retouchée en entier.
"""
import json

import frappe

from openlab_academy.infrastructure import editorjs, html_blocs, retouches_frappe

DOCTYPE = "Partie Lecon OpenLab"
CHAMP = retouches_frappe.CHAMP
LECON = retouches_frappe.LECON
_CHAMPS = ("name", "cle", "rang", "titre", "contenu", "blocs", CHAMP)


def ecrire(lecon: str, rubriques) -> None:
    """Dépose les parties d'une leçon, dans l'ordre de lecture, en remplaçant celles qui s'y trouvaient."""
    supprimer(lecon)
    for rang, rubrique in enumerate(rubriques, start=1):
        frappe.get_doc({
            "doctype": DOCTYPE, "lecon": lecon, "cle": rubrique.cle, "rang": rang,
            "titre": rubrique.titre, "contenu": html_blocs.vers_html(rubrique.blocs),
            "blocs": json.dumps(list(rubrique.blocs), ensure_ascii=False),
        }).insert(ignore_permissions=True)


def supprimer(lecon: str) -> None:
    for nom in frappe.get_all(DOCTYPE, {"lecon": lecon}, pluck="name"):
        frappe.delete_doc(DOCTYPE, nom, force=True, ignore_permissions=True, delete_permanently=True)


def oublier(doc, methode=None) -> None:
    """Hook on_trash d'une leçon : ses parties partent avec elle, sinon la republication laisse des orphelines."""
    supprimer(doc.name)


def parties(lecon: str) -> list[dict]:
    return frappe.get_all(DOCTYPE, {"lecon": lecon}, _CHAMPS, order_by="rang asc, creation asc")


def blocs(partie: dict) -> list[dict]:
    """Les blocs d'une partie : relus de l'éditeur si elle a été retouchée, sinon ceux du fichier."""
    if partie.get(CHAMP):
        return html_blocs.vers_blocs(partie.get("contenu") or "")
    try:
        lus = json.loads(partie.get("blocs") or "[]")
    except ValueError:  # colonne abîmée à la main : la partie ne rend rien plutôt que de casser la leçon
        return []
    return [b for b in lus if isinstance(b, dict)] if isinstance(lus, list) else []


def assembler(lecon: str) -> str | None:
    """Contenu de leçon assemblé depuis ses parties, ou None si la leçon n'en a pas (ancienne publication)."""
    toutes = parties(lecon)
    if not toutes:
        return None
    return editorjs.document([bloc for partie in toutes for bloc in blocs(partie)])


def appliquer(lecon: str) -> None:
    """Réécrit le contenu de la leçon depuis ses parties.

    Une leçon retouchée en entier dans l'éditeur du LMS garde la main : son drapeau l'emporte sur ses parties,
    jusqu'à ce qu'un administrateur le décoche. L'écriture se fait sous le drapeau de publication, pour que
    reposer la leçon ne la marque pas elle-même comme retouchée."""
    if frappe.db.get_value(LECON, lecon, CHAMP):
        return
    contenu = assembler(lecon)
    if contenu is None:
        return
    with retouches_frappe.publication():
        frappe.db.set_value(LECON, lecon, "content", contenu)


def marquer(doc, methode=None) -> None:
    """Hook on_update d'une partie : pose la case de retouche et met la leçon à jour pour les apprenants."""
    if frappe.flags.get(retouches_frappe.DRAPEAU):
        return
    avant = doc.get_doc_before_save()
    if avant is not None and (avant.get("contenu") or "") != (doc.get("contenu") or "") and not doc.get(CHAMP):
        frappe.db.set_value(DOCTYPE, doc.name, CHAMP, 1, update_modified=False)
        doc.reload()
    appliquer(doc.lecon)


def rattraper() -> int:
    """Donne ses parties à toute leçon qui n'en a pas encore, en découpant le contenu qu'elle porte en base.

    Deux cas : les parcours publiés avant les parties, et ceux qu'une cohorte en cours interdit de republier.
    Le contenu est repris tel quel, jamais régénéré depuis le fichier de parcours : un inscrit ne voit rien
    changer, et chaque rubrique devient éditable."""
    rattrapees = 0
    for lecon in frappe.get_all(LECON, ["name", "content"]):
        if frappe.db.count(DOCTYPE, {"lecon": lecon.name}):
            continue
        rubriques = editorjs.decouper(_blocs_du_contenu(lecon.content))
        if rubriques:
            ecrire(lecon.name, rubriques)
            rattrapees += 1
    return rattrapees


def _blocs_du_contenu(contenu: str | None) -> list[dict]:
    try:
        document = json.loads(contenu or "")
    except ValueError:  # une leçon écrite à la main peut porter du HTML au lieu du format du LMS
        return []
    blocs_lus = document.get("blocks") if isinstance(document, dict) else None
    return [b for b in blocs_lus if isinstance(b, dict)] if isinstance(blocs_lus, list) else []


# --- republication -----------------------------------------------------------------------------------------------

def relever(cours_id: str) -> dict[tuple[str, str], str]:
    """{(titre de la leçon, clé de la partie): contenu} des parties retouchées, avant que la purge ne les emporte."""
    retouchees: dict[tuple[str, str], str] = {}
    for lecon in frappe.get_all(LECON, {"course": cours_id}, ["name", "title"]):
        for partie in frappe.get_all(DOCTYPE, {"lecon": lecon.name, CHAMP: 1}, ["cle", "contenu"]):
            if partie.contenu:
                retouchees[(lecon.title, partie.cle)] = partie.contenu
    return retouchees


def reconduire(cours_id: str, retouchees: dict[tuple[str, str], str],
               remplacements: dict[str, str] | None = None) -> None:
    """Repose les parties retouchées sur les leçons que la republication vient de recréer."""
    if not retouchees:
        return
    touchees = set()
    for (titre, cle), contenu in retouchees.items():
        lecon = frappe.db.get_value(LECON, {"course": cours_id, "title": titre})
        if not lecon:  # la séance a disparu du fichier de parcours : rien à reconduire
            continue
        nom = frappe.db.get_value(DOCTYPE, {"lecon": lecon, "cle": cle})
        if not nom:  # la rubrique a disparu de la séance
            continue
        for ancien, nouveau in (remplacements or {}).items():
            contenu = contenu.replace(ancien, nouveau)
        frappe.db.set_value(DOCTYPE, nom, {"contenu": contenu, CHAMP: 1})
        touchees.add(lecon)
    for lecon in touchees:
        appliquer(lecon)
