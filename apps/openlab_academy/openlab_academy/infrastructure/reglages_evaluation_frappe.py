"""Adaptateur : console de l'évaluation (réglages, surcharges, délégations) <-> value objects du domaine."""
import json

import frappe
from frappe.utils import get_datetime
from frappe.utils.password import get_decrypted_password

from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, Chaine, ConfigEtape, ConfigIA, Etape, Expiration, ReglagesEvaluation, Surcharge, TypeExercice)

REGLAGES = "Reglages Evaluation OpenLab"
SURCHARGE = "Surcharge Evaluation OpenLab"
DELEGATION = "Delegation OpenLab"
ROLE = "Responsable pédagogique OpenLab"
ESPACE = "Évaluation OpenLab"
ECRANS = (REGLAGES, SURCHARGE, DELEGATION, "Journal Note OpenLab", "Reglages OpenLab Academy",
          "Ouverture Lecon OpenLab")


def _lignes(texte) -> tuple[str, ...]:
    return tuple(ligne.strip() for ligne in (texte or "").splitlines() if ligne.strip())


def _config(ligne) -> ConfigEtape:
    return ConfigEtape(Etape(ligne.etape), bool(ligne.active), int(ligne.delai_heures or 0),
                       Expiration(ligne.expiration))


def _chaine(doc, lignes) -> Chaine:
    return Chaine(tuple(_config(ligne) for ligne in lignes), nb_pairs=int(doc.nb_pairs or 0),
                  anonymat=bool(doc.anonymat), note_masquee_avant_relectures=bool(doc.note_masquee_avant_relectures),
                  note_sur=int(doc.note_sur or 0), seuil_reussite=float(doc.seuil_reussite or 0))


def vers_domaine(doc) -> ReglagesEvaluation:
    par_type: dict[TypeExercice, list] = {}
    for ligne in doc.etapes:
        if not ligne.type_exercice:
            raise ReglagesInvalides("chaque étape doit préciser son type d'exercice")
        par_type.setdefault(TypeExercice(ligne.type_exercice), []).append(ligne)
    return ReglagesEvaluation(
        chaines={type_: _chaine(doc, lignes) for type_, lignes in par_type.items()},
        ia=ConfigIA(url=doc.ia_url or "", modele_texte=doc.ia_modele_texte or "", modele_code=doc.ia_modele_code or "",
                    delai_minutes=int(doc.ia_delai_minutes or 0), seuil_confiance=float(doc.ia_seuil_confiance or 0),
                    tournures_injection=tuple(t.texte for t in doc.tournures),
                    plafond_caracteres=int(doc.ia_plafond_caracteres or 0)),
        publication_provisoire=bool(doc.publication_provisoire),
        responsable_pedagogique=doc.responsable_pedagogique or "", hotes_depots=_lignes(doc.hotes_depots),
        grille_generique=tuple((c.nom, int(c.poids or 0)) for c in doc.grille_generique),
        niveaux_generiques=_lignes(doc.niveaux_generiques),
    )


def surcharge_vers_domaine(doc) -> Surcharge:
    return Surcharge(doc.cohorte or None, doc.exercice or None, _chaine(doc, doc.etapes))


def charger() -> ReglagesEvaluation:
    doc = frappe.get_single(REGLAGES)
    return vers_domaine(doc) if doc.get("etapes") else ReglagesEvaluation()


def surcharges() -> tuple[Surcharge, ...]:
    return tuple(surcharge_vers_domaine(frappe.get_doc(SURCHARGE, nom))
                 for nom in frappe.get_all(SURCHARGE, pluck="name", order_by="creation"))


def delegations() -> tuple[Delegation, ...]:
    champs = ["titulaire", "delegataire", "debut", "fin", "cohorte", "exercice", "revoquee"]
    return tuple(Delegation(d.titulaire, d.delegataire, get_datetime(d.debut), get_datetime(d.fin),
                            cohorte=d.cohorte or None, exercice=d.exercice or None, revoquee=bool(d.revoquee))
                 for d in frappe.get_all(DELEGATION, fields=champs, order_by="creation"))


def cle_ia() -> str:
    return get_decrypted_password(REGLAGES, REGLAGES, "cle_ia", raise_exception=False) or ""


def initialiser() -> None:
    """Remplit la console avec les valeurs par défaut du domaine, sans jamais écraser des réglages existants."""
    doc = frappe.get_single(REGLAGES)
    if doc.get("etapes"):
        return
    defaut = ReglagesEvaluation()
    chaine, ia = CHAINES_DEFAUT[TypeExercice.LIVRABLE], defaut.ia
    doc.update({
        "nb_pairs": chaine.nb_pairs, "anonymat": chaine.anonymat, "note_sur": chaine.note_sur,
        "note_masquee_avant_relectures": chaine.note_masquee_avant_relectures,
        "seuil_reussite": chaine.seuil_reussite, "publication_provisoire": defaut.publication_provisoire,
        "ia_url": ia.url, "ia_modele_texte": ia.modele_texte, "ia_modele_code": ia.modele_code,
        "ia_delai_minutes": ia.delai_minutes, "ia_seuil_confiance": ia.seuil_confiance,
        "ia_plafond_caracteres": ia.plafond_caracteres, "hotes_depots": "\n".join(defaut.hotes_depots),
        "niveaux_generiques": "\n".join(defaut.niveaux_generiques),
    })
    doc.set("etapes", [{"type_exercice": type_.value, "etape": c.etape.value, "active": c.active,
                        "delai_heures": c.delai_heures, "expiration": c.expiration.value}
                       for type_, ch in CHAINES_DEFAUT.items() for c in ch.etapes])
    doc.set("tournures", [{"texte": t} for t in ia.tournures_injection])
    doc.set("grille_generique", [{"nom": nom, "poids": poids} for nom, poids in defaut.grille_generique])
    doc.save(ignore_permissions=True)


def creer_role() -> None:
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def creer_espace_travail() -> None:
    """Espace « Évaluation OpenLab » : raccourcis vers les six écrans de la console (créé une seule fois)."""
    if frappe.db.exists("Workspace", ESPACE):
        return
    blocs = [{"id": f"raccourci{i}", "type": "shortcut", "data": {"shortcut_name": ecran, "col": 4}}
             for i, ecran in enumerate(ECRANS)]
    frappe.get_doc({
        "doctype": "Workspace", "name": ESPACE, "label": ESPACE, "title": ESPACE, "module": "OpenLab Academy",
        "public": 1, "content": json.dumps(blocs, ensure_ascii=False),
        "shortcuts": [{"label": ecran, "type": "DocType", "link_to": ecran, "doc_view": "List"} for ecran in ECRANS],
    }).insert(ignore_permissions=True)


def preparer() -> None:
    """Rôle, réglages par défaut et espace de travail : idempotent, appelé par le patch et après chaque migration."""
    creer_role()
    initialiser()
    creer_espace_travail()
