"""Adaptateur : console de l'évaluation (réglages, surcharges, délégations) <-> value objects du domaine."""
import json

import frappe
from frappe.utils import get_datetime
from frappe.utils.password import get_decrypted_password

from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, GRILLE_GENERIQUE_DEFAUT, Chaine, ConfigEtape, ConfigIA, Etape, Expiration, ReglagesEvaluation,
    Surcharge, TypeExercice, TOURNURES_DEFAUT)

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


def _chaine(params, lignes) -> Chaine:
    """`params` porte nb_pairs, anonymat, etc. : la ligne du type (réglages) ou la surcharge elle-même."""
    return Chaine(tuple(_config(ligne) for ligne in lignes), nb_pairs=int(params.nb_pairs or 0),
                  anonymat=bool(params.anonymat),
                  note_masquee_avant_relectures=bool(params.note_masquee_avant_relectures),
                  note_sur=int(params.note_sur or 0), seuil_reussite=float(params.seuil_reussite or 0),
                  attente_max_heures=int(params.attente_max_heures or 0))


def vers_domaine(doc) -> ReglagesEvaluation:
    par_type: dict[TypeExercice, list] = {}
    for ligne in doc.etapes:
        if not ligne.type_exercice:
            raise ReglagesInvalides("chaque étape doit préciser son type d'exercice")
        par_type.setdefault(TypeExercice(ligne.type_exercice), []).append(ligne)
    defaut = ReglagesEvaluation()
    params = {p.type_exercice: p for p in doc.parametres}
    if len(params) != len(doc.parametres):
        raise ReglagesInvalides("un seul jeu de paramètres par type d'exercice")
    return ReglagesEvaluation(
        chaines={type_: _chaine(params.get(type_.value) or CHAINES_DEFAUT[type_], lignes) for type_, lignes in par_type.items()},
        ia=ConfigIA(url=doc.ia_url or "", modele_texte=doc.ia_modele_texte or "", modele_code=doc.ia_modele_code or "",
                    delai_minutes=int(doc.ia_delai_minutes or 0), seuil_confiance=float(doc.ia_seuil_confiance or 0),
                    tournures_injection=tuple(t.texte for t in doc.tournures) or TOURNURES_DEFAUT,
                    plafond_caracteres=int(doc.ia_plafond_caracteres or 0),
                    contexte_tokens=int(doc.contexte_ia_tokens or 0) or defaut.ia.contexte_tokens),
        publication_provisoire=bool(doc.publication_provisoire),
        responsable_pedagogique=doc.responsable_pedagogique or "", hotes_depots=_lignes(doc.hotes_depots) or defaut.hotes_depots,
        longueur_min_caracteres=int(doc.longueur_min_caracteres or 0),
        grille_generique=tuple((c.nom, int(c.poids or 0)) for c in doc.grille_generique) or GRILLE_GENERIQUE_DEFAUT,
        niveaux_generiques=_lignes(doc.niveaux_generiques) or defaut.niveaux_generiques,
    )


def surcharge_vers_domaine(doc) -> Surcharge:
    """Une surcharge sans étapes ne porte qu'un suppléant : la chaîne de la cible reste celle du YAML ou du type."""
    chaine = _chaine(doc, doc.etapes) if doc.etapes else None
    return Surcharge(doc.cohorte or None, doc.exercice or None, chaine, doc.suppleant or None)


def charger() -> ReglagesEvaluation:
    doc = frappe.get_single(REGLAGES)
    return vers_domaine(doc)


def surcharges() -> tuple[Surcharge, ...]:
    return tuple(surcharge_vers_domaine(frappe.get_doc(SURCHARGE, nom))
                 for nom in frappe.get_all(SURCHARGE, pluck="name", order_by="creation"))


CHAMPS_DELEGATION = ["titulaire", "delegataire", "debut", "fin", "cohorte", "exercice", "revoquee"]


def _delegation(d) -> Delegation:
    return Delegation(d.titulaire, d.delegataire, get_datetime(d.debut), get_datetime(d.fin),
                      cohorte=d.cohorte or None, exercice=d.exercice or None, revoquee=bool(d.revoquee))


def delegations() -> tuple[Delegation, ...]:
    return tuple(_delegation(d) for d in frappe.get_all(DELEGATION, fields=CHAMPS_DELEGATION, order_by="creation"))


class DepotDelegationsFrappe:
    def creer_delegation(self, d: Delegation) -> str:
        return frappe.get_doc({"doctype": DELEGATION, "titulaire": d.titulaire, "delegataire": d.delegataire,
                               "debut": d.debut, "fin": d.fin, "cohorte": d.cohorte, "exercice": d.exercice}
                              ).insert(ignore_permissions=True).name

    def delegation(self, delegation_id: str) -> Delegation | None:
        ligne = frappe.db.get_value(DELEGATION, delegation_id, CHAMPS_DELEGATION, as_dict=True)
        return _delegation(ligne) if ligne else None

    def revoquer_delegation(self, delegation_id: str) -> None:
        frappe.db.set_value(DELEGATION, delegation_id, "revoquee", 1)


class SourceReglagesFrappe:
    """Réglages et surcharges relus à chaque usage : la console s'applique sans redémarrage."""

    def reglages(self) -> ReglagesEvaluation:
        return charger()

    def surcharges(self) -> tuple[Surcharge, ...]:
        return surcharges()


def cle_ia() -> str:
    return get_decrypted_password(REGLAGES, REGLAGES, "cle_ia", raise_exception=False) or ""


def jeton_depots() -> str:
    """Jeton d'accès facultatif à l'API GitHub (champ mot de passe) : relève le quota des appels anonymes."""
    return get_decrypted_password(REGLAGES, REGLAGES, "jeton_depots", raise_exception=False) or ""


def _remplir_parametres(doc) -> None:
    doc.set("parametres", [{"type_exercice": type_.value, "nb_pairs": ch.nb_pairs, "anonymat": ch.anonymat,
                            "note_masquee_avant_relectures": ch.note_masquee_avant_relectures,
                            "note_sur": ch.note_sur, "seuil_reussite": ch.seuil_reussite,
                            "attente_max_heures": ch.attente_max_heures}
                           for type_, ch in CHAINES_DEFAUT.items()])


def initialiser() -> None:
    """Remplit la console avec les valeurs par défaut du domaine, sans jamais écraser des réglages existants."""
    doc = frappe.get_single(REGLAGES)
    if doc.get("etapes"):
        if not doc.get("parametres"):  # site créé avant les paramètres par type
            _remplir_parametres(doc)
            doc.save(ignore_permissions=True)
        return
    defaut = ReglagesEvaluation()
    ia = defaut.ia
    doc.update({
        "publication_provisoire": defaut.publication_provisoire,
        "ia_url": ia.url, "ia_modele_texte": ia.modele_texte, "ia_modele_code": ia.modele_code,
        "ia_delai_minutes": ia.delai_minutes, "ia_seuil_confiance": ia.seuil_confiance,
        "ia_plafond_caracteres": ia.plafond_caracteres, "contexte_ia_tokens": ia.contexte_tokens,
        "hotes_depots": "\n".join(defaut.hotes_depots),
        "niveaux_generiques": "\n".join(defaut.niveaux_generiques),
        "longueur_min_caracteres": defaut.longueur_min_caracteres,
    })
    doc.set("etapes", [{"type_exercice": type_.value, "etape": c.etape.value, "active": c.active,
                        "delai_heures": c.delai_heures, "expiration": c.expiration.value}
                       for type_, ch in CHAINES_DEFAUT.items() for c in ch.etapes])
    _remplir_parametres(doc)
    doc.set("tournures", [{"texte": t} for t in ia.tournures_injection])
    doc.set("grille_generique", [{"nom": nom, "poids": poids} for nom, poids in defaut.grille_generique])
    doc.save(ignore_permissions=True)


def completer_champs() -> None:
    """Champ ajouté après l'initialisation d'un site : il reçoit le défaut du domaine, jamais par-dessus une valeur réglée."""
    if not frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field='longueur_min_caracteres'", REGLAGES):
        frappe.db.set_single_value(REGLAGES, "longueur_min_caracteres", ReglagesEvaluation().longueur_min_caracteres)


def creer_role() -> None:
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def _restreindre_espace(espace) -> None:
    """Un espace créé par une version antérieure reçoit la restriction de rôles prévue."""
    voulus = {"System Manager", ROLE}
    if {r.role for r in espace.roles} != voulus or not espace.public:
        espace.public = 1
        espace.set("roles", [{"role": r} for r in sorted(voulus)])
        espace.save(ignore_permissions=True)


def creer_espace_travail() -> None:
    """Espace « Évaluation OpenLab » : raccourcis vers les six écrans de la console (créé une seule fois)."""
    if frappe.db.exists("Workspace", ESPACE):
        _restreindre_espace(frappe.get_doc("Workspace", ESPACE))
        return
    blocs = [{"id": f"raccourci{i}", "type": "shortcut", "data": {"shortcut_name": ecran, "col": 4}}
             for i, ecran in enumerate(ECRANS)]
    frappe.get_doc({
        "doctype": "Workspace", "name": ESPACE, "label": ESPACE, "title": ESPACE, "module": "OpenLab Academy",
        "public": 1, "roles": [{"role": "System Manager"}, {"role": ROLE}], "content": json.dumps(blocs, ensure_ascii=False),
        "shortcuts": [{"label": ecran, "type": "DocType", "link_to": ecran, "doc_view": "List"} for ecran in ECRANS],
    }).insert(ignore_permissions=True)


def preparer() -> None:
    """Rôle, réglages par défaut et espace de travail : idempotent, appelé par le patch et après chaque migration."""
    creer_role()
    initialiser()
    completer_champs()
    creer_espace_travail()
