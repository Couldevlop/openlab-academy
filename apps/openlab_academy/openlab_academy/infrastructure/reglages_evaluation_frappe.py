"""Adaptateur : console de l'évaluation (réglages, surcharges, délégations) <-> value objects du domaine."""
import json

import frappe
from frappe.utils import get_datetime
from frappe.utils.password import get_decrypted_password

from openlab_academy.domain.delegation import Delegation
from openlab_academy.domain.reglages import ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import (
    CHAINES_DEFAUT, GRILLE_GENERIQUE_DEFAUT, OPTIONS_CHAINE, ActionSouffrance, Chaine, ConfigEtape, ConfigIA, Etape,
    Expiration,
    ReglagesEvaluation, Resoumission, Surcharge, TypeExercice, TOURNURES_DEFAUT)
from openlab_academy.domain.equipe import Equipe

REGLAGES = "Reglages Evaluation OpenLab"
SURCHARGE = "Surcharge Evaluation OpenLab"
DELEGATION = "Delegation OpenLab"
EQUIPE = "Equipe Correction OpenLab"
ROLE = "Responsable pédagogique OpenLab"
ESPACE = "Évaluation OpenLab"
ECRANS = (REGLAGES, SURCHARGE, DELEGATION, "Journal Note OpenLab", "Reglages OpenLab Academy",
          "Ouverture Lecon OpenLab", EQUIPE)


def _lignes(texte) -> tuple[str, ...]:
    return tuple(ligne.strip() for ligne in (texte or "").splitlines() if ligne.strip())


def _config(ligne) -> ConfigEtape:
    return ConfigEtape(Etape(ligne.etape), bool(ligne.active), int(ligne.delai_heures or 0),
                       Expiration(ligne.expiration))


CHAMPS_PAIRS = ("pairs_attente_max_jours", "pairs_minimum_releves", "pairs_reattributions_max")
DEFAUT_CHAINE = Chaine((ConfigEtape(Etape.FORMATEUR, True, 72, Expiration.ESCALADER),))  # défauts des options


def _chaine(params, lignes) -> Chaine:
    """`params` porte nb_pairs, anonymat, etc. : la ligne du type (réglages) ou la surcharge elle-même."""
    return Chaine(tuple(_config(ligne) for ligne in lignes), nb_pairs=int(params.nb_pairs or 0),
                  anonymat=bool(params.anonymat),
                  note_masquee_avant_relectures=bool(params.note_masquee_avant_relectures),
                  note_sur=int(params.note_sur or 0), seuil_reussite=float(params.seuil_reussite or 0),
                  **{champ: _entier(getattr(params, champ, None), getattr(DEFAUT_CHAINE, champ))
                     for champ in CHAMPS_PAIRS})


def _entier(valeur, defaut: int) -> int:
    """Champ numérique de la console ; vide (site antérieur au réglage), le défaut du domaine."""
    return defaut if valeur in (None, "") else int(valeur)


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
                    contexte_tokens=int(doc.contexte_ia_tokens or 0) or defaut.ia.contexte_tokens,
                    citation_min_caracteres=_entier(doc.ia_citation_min_caracteres, defaut.ia.citation_min_caracteres)),
        publication_provisoire=bool(doc.publication_provisoire),
        responsable_pedagogique=doc.responsable_pedagogique or "", hotes_depots=_lignes(doc.hotes_depots) or defaut.hotes_depots,
        longueur_min_caracteres=int(doc.longueur_min_caracteres or 0),
        grille_generique=tuple((c.nom, int(c.poids or 0)) for c in doc.grille_generique) or GRILLE_GENERIQUE_DEFAUT,
        niveaux_generiques=_lignes(doc.niveaux_generiques) or defaut.niveaux_generiques,
        **{champ: _entier(doc.get(champ), getattr(defaut, champ)) for champ in CHAMPS_INSTANTANE},
        resoumission_jusqua=Resoumission(doc.get("resoumission_jusqua") or defaut.resoumission_jusqua),
        souffrance_action_jours=_entier(doc.get("souffrance_action_jours"), defaut.souffrance_action_jours),
        souffrance_action=ActionSouffrance(doc.get("souffrance_action") or defaut.souffrance_action),
    )


OUI_NON = {"oui": True, "non": False}
CASES = ("anonymat", "note_masquee_avant_relectures")  # cases à cocher d'avant, devenues oui / non


def _option(champ: str, brut):
    texte = str(brut).strip()
    try:
        if champ in CASES:
            return OUI_NON[texte]
        if champ == "seuil_reussite":
            return float(texte.replace(",", "."))
        return int(texte)
    except (KeyError, ValueError):
        raise ReglagesInvalides(f"{champ} : valeur invalide « {texte} »") from None


def surcharge_vers_domaine(doc) -> Surcharge:
    """Surcharge partielle : un champ vide est hérité, seules les étapes citées sont remplacées."""
    options = {c: _option(c, doc.get(c)) for c in OPTIONS_CHAINE if str(doc.get(c) or "").strip()}
    return Surcharge(doc.cohorte or None, doc.exercice or None, options, tuple(_config(ligne) for ligne in doc.etapes))


def equipe_vers_domaine(doc) -> Equipe:
    membres = sorted(doc.membres, key=lambda m: m.idx or 0)
    return Equipe(doc.cours or None, doc.cohorte or None, doc.exercice or None,
                  tuple(m.utilisateur for m in membres if m.role == "titulaire"),
                  tuple(m.utilisateur for m in membres if m.role == "suppleant"), doc.responsable or "")


def migrer_surcharges_partielles() -> None:
    """Une surcharge d'avant fixait toute la chaîne : ses valeurs restent explicites (cases à cocher en oui / non)
    et les étapes qu'elle ne citait pas, alors inactives, le deviennent explicitement. Sans étapes, elle ne portait
    qu'un suppléant : ses champs, alors ignorés, deviennent hérités. Le suppléant passe
    dans l'équipe de la cible (l'exercice s'il est visé, sinon la cohorte) ; une surcharge vide est supprimée.
    Rejouée, la migration ne touche que l'ancien format, reconnu strictement : un suppléant en colonne, ou une
    case à cocher restée en 0 / 1 (le nouveau format n'écrit que oui, non ou vide)."""
    anciens = {}
    if frappe.db.has_column(SURCHARGE, "suppleant"):
        anciens = dict(frappe.db.sql(f"select name, suppleant from `tab{SURCHARGE}` where ifnull(suppleant, '') != ''"))
    for nom in frappe.get_all(SURCHARGE, pluck="name", order_by="creation"):
        doc = frappe.get_doc(SURCHARGE, nom)
        if not (nom in anciens or any(str(doc.get(c) or "").strip() in ("0", "1") for c in CASES)):
            continue  # déjà au nouveau format
        for champ in OPTIONS_CHAINE:
            valeur = str(doc.get(champ) or "").strip()
            if not doc.etapes:
                doc.set(champ, "")
            elif champ in CASES and valeur in ("0", "1"):
                doc.set(champ, "oui" if valeur == "1" else "non")
        citees = {ligne.etape for ligne in doc.etapes}
        for etape in (e for e in Etape if doc.etapes and e.value not in citees):
            doc.append("etapes", {"etape": etape.value, "active": 0, "delai_heures": 0, "expiration": "passer"})
        if anciens.get(nom):
            _ajouter_suppleant(doc.exercice, None if doc.exercice else doc.cohorte, anciens[nom])
        if doc.etapes or any(str(doc.get(c) or "").strip() for c in OPTIONS_CHAINE):
            doc.flags.ignore_validate = True  # valeurs reprises telles quelles : la migration ne bloque jamais
            doc.save(ignore_permissions=True)
        else:
            frappe.delete_doc(SURCHARGE, nom, ignore_permissions=True, force=True)
    if anciens:
        frappe.db.sql(f"update `tab{SURCHARGE}` set suppleant = null")


def _ajouter_suppleant(exercice: str | None, cohorte: str | None, suppleant: str) -> None:
    filtres = {"exercice": exercice or ["is", "not set"], "cohorte": cohorte or ["is", "not set"],
               "cours": ["is", "not set"]}
    nom = frappe.db.get_value(EQUIPE, filtres)
    doc = frappe.get_doc(EQUIPE, nom) if nom else frappe.get_doc({"doctype": EQUIPE, "exercice": exercice,
                                                                 "cohorte": cohorte})
    if suppleant not in [m.utilisateur for m in doc.membres]:
        doc.append("membres", {"utilisateur": suppleant, "role": "suppleant"})
    doc.save(ignore_permissions=True)


def equipes() -> tuple[Equipe, ...]:
    return tuple(equipe_vers_domaine(frappe.get_doc(EQUIPE, nom))
                 for nom in frappe.get_all(EQUIPE, pluck="name", order_by="creation"))


def exercice_type_yaml(exercice: str) -> tuple[TypeExercice, Chaine | None] | None:
    """Type et chaîne YAML d'un exercice publié, pour revalider les surcharges qui le visent."""
    from openlab_academy.infrastructure.depot_copies_frappe import DepotCopiesFrappe
    connu = DepotCopiesFrappe().exercice(exercice)
    return (connu.type_, connu.chaine) if connu else None


def liste_fautives(fautives: list[tuple[str, str]]) -> str:
    return " ; ".join(f"{libelle} ({motif})" for libelle, motif in fautives)


def charger() -> ReglagesEvaluation:
    doc = frappe.get_single(REGLAGES)
    return vers_domaine(doc)


def surcharges_nommees() -> tuple[tuple[str, Surcharge], ...]:
    return tuple((nom, surcharge_vers_domaine(frappe.get_doc(SURCHARGE, nom)))
                 for nom in frappe.get_all(SURCHARGE, pluck="name", order_by="creation"))


def surcharges() -> tuple[Surcharge, ...]:
    return tuple(s for _, s in surcharges_nommees())


CHAMPS_DELEGATION = ["titulaire", "delegataire", "debut", "fin", "cours", "cohorte", "exercice", "revoquee"]


def delegation_vers_domaine(d) -> Delegation:
    """Ligne ou document de délégation ; une fin absente reste absente (la règle du domaine la refuse)."""
    return Delegation(d.titulaire, d.delegataire, get_datetime(d.debut), get_datetime(d.fin) if d.fin else None,
                      cohorte=d.cohorte or None, exercice=d.exercice or None, revoquee=bool(d.revoquee),
                      cours=d.cours or None)


def delegations() -> tuple[Delegation, ...]:
    return tuple(delegation_vers_domaine(d)
                 for d in frappe.get_all(DELEGATION, fields=CHAMPS_DELEGATION, order_by="creation"))


class DepotDelegationsFrappe:
    def creer_delegation(self, d: Delegation) -> str:
        return frappe.get_doc({"doctype": DELEGATION, "titulaire": d.titulaire, "delegataire": d.delegataire,
                               "debut": d.debut, "fin": d.fin, "cours": d.cours, "cohorte": d.cohorte,
                               "exercice": d.exercice}).insert(ignore_permissions=True).name

    def delegation(self, delegation_id: str) -> Delegation | None:
        ligne = frappe.db.get_value(DELEGATION, delegation_id, CHAMPS_DELEGATION, as_dict=True)
        return delegation_vers_domaine(ligne) if ligne else None

    def revoquer_delegation(self, delegation_id: str) -> None:
        """Par le document : le contrôleur consigne et prévient, comme depuis l'écran de la console."""
        doc = frappe.get_doc(DELEGATION, delegation_id)
        doc.revoquee = 1
        doc.save(ignore_permissions=True)


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
                            **{champ: getattr(ch, champ) for champ in CHAMPS_PAIRS}}
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
        **_champs_completes(defaut),
    })
    doc.set("etapes", [{"type_exercice": type_.value, "etape": c.etape.value, "active": c.active,
                        "delai_heures": c.delai_heures, "expiration": c.expiration.value}
                       for type_, ch in CHAINES_DEFAUT.items() for c in ch.etapes])
    _remplir_parametres(doc)
    doc.set("tournures", [{"texte": t} for t in ia.tournures_injection])
    doc.set("grille_generique", [{"nom": nom, "poids": poids} for nom, poids in defaut.grille_generique])
    doc.save(ignore_permissions=True)


CHAMPS_INSTANTANE = ("instantane_fichiers_max", "instantane_delai_s", "instantane_budget_tache_s",
                     "remise_par_heure", "remise_regroupement_s")  # même nom dans la console et dans le domaine


def _champs_completes(defaut: ReglagesEvaluation) -> dict:
    """Champs de la console ajoutés après l'initialisation des premiers sites, avec le défaut du domaine."""
    return {"longueur_min_caracteres": defaut.longueur_min_caracteres,
            "ia_citation_min_caracteres": defaut.ia.citation_min_caracteres,
            **{champ: getattr(defaut, champ) for champ in CHAMPS_INSTANTANE},
            "resoumission_jusqua": defaut.resoumission_jusqua.value,
            "souffrance_action_jours": defaut.souffrance_action_jours,
            "souffrance_action": defaut.souffrance_action.value}


def completer_champs() -> None:
    """Champ ajouté après l'initialisation d'un site : il reçoit le défaut du domaine, jamais par-dessus une valeur
    réglée (même nulle)."""
    for champ, valeur in _champs_completes(ReglagesEvaluation()).items():
        if not frappe.db.sql("select 1 from `tabSingles` where doctype=%s and field=%s", (REGLAGES, champ)):
            frappe.db.set_single_value(REGLAGES, champ, valeur)


def creer_role() -> None:
    if not frappe.db.exists("Role", ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1}).insert(ignore_permissions=True)


def _raccourci(i: int, ecran: str) -> dict:
    return {"id": f"raccourci{i}", "type": "shortcut", "data": {"shortcut_name": ecran, "col": 4}}


def _restreindre_espace(espace) -> None:
    """Un espace créé par une version antérieure reçoit la restriction de rôles prévue et les écrans ajoutés
    depuis."""
    voulus, modifie = {"System Manager", ROLE}, False
    if {r.role for r in espace.roles} != voulus or not espace.public:
        espace.public = 1
        espace.set("roles", [{"role": r} for r in sorted(voulus)])
        modifie = True
    presents = {s.link_to for s in espace.shortcuts}
    blocs = json.loads(espace.content or "[]")
    for ecran in (e for e in ECRANS if e not in presents):
        espace.append("shortcuts", {"label": ecran, "type": "DocType", "link_to": ecran, "doc_view": "List"})
        blocs.append(_raccourci(len(blocs), ecran))
        modifie = True
    if modifie:
        espace.content = json.dumps(blocs, ensure_ascii=False)
        espace.save(ignore_permissions=True)


def creer_espace_travail() -> None:
    """Espace « Évaluation OpenLab » : raccourcis vers les écrans de la console (créé une seule fois)."""
    if frappe.db.exists("Workspace", ESPACE):
        _restreindre_espace(frappe.get_doc("Workspace", ESPACE))
        return
    blocs = [_raccourci(i, ecran) for i, ecran in enumerate(ECRANS)]
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
