"""Jeu d'essai du banc de développement : de quoi remplir les neuf écrans de l'espace.

    bench --site lms.localhost execute openlab_academy.entrypoints.jeu_essai.run

À côté de `seed.py`, qui publie les parcours depuis les YAML : celui-ci ne touche ni aux parcours, ni aux
réglages, ni au catalogue. Il ne crée que ce qu'une académie produit à l'usage — des copies, leurs
propositions de note, des relectures entre pairs, une équipe de correction, des dossiers de paiement et
leurs versements — pour qu'un écran vide ne puisse plus passer pour un écran qui marche.

Relançable : il purge d'abord ce qu'il a lui-même créé. Les copies qu'il pose portent le préfixe `MARQUE`
dans leur soumission, et c'est à ce préfixe seul qu'il les reconnaît : une copie déposée autrement lui
survit.

Le plan des données est séparé de leur écriture. Les constantes ci-dessous se lisent sans Frappe et sans
base, et `test_jeu_essai.py` les tient : un lot qui ne se formerait plus, un dossier de paiement pose sur
le parcours gratuit ou un écran que plus aucune donnée n'atteint cassent la suite, au lieu de se
découvrir dans le navigateur.

Le mot de passe du formateur d'essai n'est pas écrit ici, et ne doit jamais l'être : `run` le tire au sort
et l'affiche une fois, ou reprend celui que `OPENLAB_MDP_ESSAI` lui donne.
"""
import json
import os
import secrets
import string

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, nowdate

MARQUE = "ESSAI-"

# --- le décor : ce que `seed.run` a déjà publié -----------------------------------------------------------
# Rien n'est codé en dur : les identifiants d'un devoir ou d'une cohorte sont tirés à la publication et
# diffèrent d'un banc à l'autre. Les noms ci-dessous ne sont que des préférences ; `_decor()` retombe sur
# le premier enregistrement qui convient, et refuse clairement si le banc n'a pas encore été ensemencé.
EXERCICE_PREFERE = "ASG-27985"
COURS_MOOC = "ia-agentique-comprendre-concevoir-et-ma-triser-les-agents-ia"  # gratuit : aucun paiement
COURS_PAYANT = "d-veloppeur-python"  # porte un tarif
TYPE_EXERCICE = "mise_en_situation"

# --- les personnes ----------------------------------------------------------------------------------------
VISITEUSE = "awa.kone@exemple.ci"  # apprenante : relecture, retour, paiement
APPRENANTS = (
    (VISITEUSE, "Awa", "Koné"),
    ("kouadio.yao@exemple.ci", "Kouadio", "Yao"),
    ("fatou.traore@exemple.ci", "Fatou", "Traoré"),
    ("ibrahim.cisse@exemple.ci", "Ibrahim", "Cissé"),
)
FORMATEUR = "formateur.essai@exemple.ci"  # correction, lots, intendance, finances, pilotage
ROLES_FORMATEUR = ("System Manager", "Intendant OpenLab")

# --- les niveaux, par critère de la grille de l'exercice ---------------------------------------------------
CRITERES = ("pertinence", "rigueur", "clarte", "ancrage_dans_le_contexte_ivoirien")
BON = {c: 2 for c in CRITERES}
MOYEN = {c: 1 for c in CRITERES}
ECART = {**BON, "rigueur": 0}  # l'IA s'écarte des pairs sur un critère

# Un lot ne se forme qu'à partir de DEUX copies de même vecteur IA dont la confiance passe le seuil
# (domain/copie.py : `lots`). Une seule copie « propre » laisserait l'écran des lots vide.
CONFIANCE_LOT = 0.91

CONTENU = (
    "Note de cadrage : agent de relance des paiements pour une PME d'Abidjan.\n\n"
    "Le marché visé est la relance des factures impayées chez les PME de Treichville. "
    "L'agent lit les factures, classe les retards et propose un message de relance."
)

# --- le plan : une entrée par écran à remplir --------------------------------------------------------------
# `ecran` ne sert qu'à la lecture et au test : il dit ce que la donnée fait exister dans l'interface.
COPIES = (
    {"cle": "lot_1", "apprenant": APPRENANTS[1][0], "statut": "a_corriger", "etape": "formateur",
     "ecran": "correcteur", "ia": BON, "confiance": CONFIANCE_LOT + 0.02, "pair": APPRENANTS[2][0]},
    {"cle": "lot_2", "apprenant": APPRENANTS[2][0], "statut": "a_corriger", "etape": "formateur",
     "ecran": "lots", "ia": BON, "confiance": CONFIANCE_LOT, "pair": APPRENANTS[1][0]},
    {"cle": "lot_3", "apprenant": APPRENANTS[3][0], "statut": "a_corriger", "etape": "formateur",
     "ecran": "lots", "ia": BON, "confiance": CONFIANCE_LOT, "pair": APPRENANTS[1][0]},
    {"cle": "ecart", "apprenant": APPRENANTS[2][0], "statut": "a_corriger", "etape": "formateur",
     "ecran": "correcteur", "ia": ECART, "confiance": 0.61, "pair": APPRENANTS[3][0]},
    {"cle": "relue", "apprenant": APPRENANTS[2][0], "statut": "en_relecture", "etape": "pairs",
     "ecran": "relecture"},
    {"cle": "publiee", "apprenant": VISITEUSE, "statut": "publiee", "etape": None,
     "ecran": "retour", "ia": MOYEN, "confiance": 0.84, "pair": APPRENANTS[3][0],
     "note": 14.0, "note_sur": 20, "reussite": 1},
    {"cle": "souffrance", "apprenant": APPRENANTS[3][0], "statut": "a_corriger", "etape": "formateur",
     "ecran": "pilotage", "souffrance": True},
)

RELECTURES = (
    {"copie": "relue", "relecteur": VISITEUSE, "statut": "à_faire", "jours": 4},
    {"copie": "relue", "relecteur": APPRENANTS[3][0], "statut": "faite", "jours": -1},
)

# Les dossiers ne se posent que sur le parcours payant : sur un parcours gratuit, l'écran de paiement
# répond « aucun paiement » et l'intendance afficherait une somme due qui n'existe pas.
DOSSIERS = (
    {"apprenant": VISITEUSE, "mode": "deux_tranches", "dispense": 0, "ecran": "paiement"},
    {"apprenant": APPRENANTS[1][0], "mode": "mensuel", "dispense": 0, "ecran": "intendance"},
    {"apprenant": APPRENANTS[2][0], "mode": "une_fois", "dispense": 0, "ecran": "intendance"},
    {"apprenant": APPRENANTS[3][0], "mode": "deux_tranches", "dispense": 1, "ecran": "intendance"},
)

VERSEMENTS = (
    {"apprenant": APPRENANTS[2][0], "montant": 300000, "moyen": "virement", "ecran": "finances"},
    {"apprenant": VISITEUSE, "montant": 160000, "moyen": "virement", "ecran": "finances"},
    {"apprenant": APPRENANTS[1][0], "montant": 60000, "moyen": "cinetpay", "ecran": "finances"},
)

TARIF = {"frais_inscription": 25000, "prix_une_fois": 300000, "prix_deux_tranches": 320000,
         "prix_mensuel": 60000}

ECRANS = ("accueil", "relecture", "correcteur", "lots", "retour", "paiement", "intendance", "finances",
          "pilotage")


def lot_attendu() -> tuple[str, ...]:
    """Clés des copies qui doivent se regrouper en un lot validable d'un geste."""
    groupes: dict[tuple, list[str]] = {}
    for c in COPIES:
        if c["statut"] == "a_corriger" and c.get("confiance", 0) >= CONFIANCE_LOT:
            groupes.setdefault(tuple(sorted(c["ia"].items())), []).append(c["cle"])
    return tuple(cle for cles in groupes.values() if len(cles) > 1 for cle in cles)


# --- l'écriture -------------------------------------------------------------------------------------------
def _mot_de_passe() -> str:
    donne = os.environ.get("OPENLAB_MDP_ESSAI")
    if donne:
        return donne
    alphabet = string.ascii_letters + string.digits
    return "Essai-" + "".join(secrets.choice(alphabet) for _ in range(16))


def _utilisateur(courriel: str, prenom: str, nom: str) -> None:
    if frappe.db.exists("User", courriel):
        return
    frappe.get_doc({"doctype": "User", "email": courriel, "first_name": prenom, "last_name": nom,
                    "send_welcome_email": 0, "enabled": 1}).insert(ignore_permissions=True)


def _formateur(mot_de_passe: str) -> None:
    _utilisateur(FORMATEUR, "Formateur", "Essai")
    doc = frappe.get_doc("User", FORMATEUR)
    tenus = {r.role for r in doc.roles}
    for role in ROLES_FORMATEUR:
        if role not in tenus and frappe.db.exists("Role", role):
            doc.append("roles", {"role": role})
    doc.new_password = mot_de_passe  # invalide les sessions ouvertes de ce compte : il faut se reconnecter
    doc.save(ignore_permissions=True)


def _purger() -> None:
    for doctype in ("Relecture Pair OpenLab", "Proposition OpenLab", "Equipe Correction OpenLab"):
        for nom in frappe.get_all(doctype, pluck="name"):
            frappe.delete_doc(doctype, nom, force=True, ignore_permissions=True)
    for nom in frappe.get_all("Copie OpenLab", {"soumission": ["like", MARQUE + "%"]}, pluck="name"):
        frappe.delete_doc("Copie OpenLab", nom, force=True, ignore_permissions=True)
    # dossiers posés par un essai précédent sur le parcours gratuit : aucun paiement ne s'y joue
    for cours in (COURS_MOOC, COURS_PAYANT):
        for nom in frappe.get_all("Dossier Paiement OpenLab", {"cours": cours}, pluck="name"):
            frappe.delete_doc("Dossier Paiement OpenLab", nom, force=True, ignore_permissions=True)


def _decor() -> dict:
    """Le devoir sur lequel tout se joue, sa grille et une cohorte : lus dans le banc, jamais devinés."""
    grilles = frappe.get_all("Grille Exercice OpenLab", {"type_exercice": TYPE_EXERCICE},
                             ["exercice", "grille_json"], order_by="exercice")
    if not grilles:
        raise frappe.ValidationError(
            f"aucune grille « {TYPE_EXERCICE} » dans ce banc : lancer d'abord "
            "openlab_academy.entrypoints.seed.run")
    choisie = next((g for g in grilles if g.exercice == EXERCICE_PREFERE), grilles[0])
    cours = frappe.db.get_value("LMS Assignment", choisie.exercice, "course")
    cohortes = frappe.get_all("Batch Course", {"course": cours}, pluck="parent",
                              parent_doctype="LMS Batch") if cours else []
    return {"exercice": choisie.exercice, "grille": choisie.grille_json or "{}",
            "cohorte": cohortes[0] if cohortes else None}


def _tarif() -> None:
    if frappe.db.exists("Tarif Parcours OpenLab", COURS_PAYANT):
        return
    frappe.get_doc({"doctype": "Tarif Parcours OpenLab", "cours": COURS_PAYANT, **TARIF}
                   ).insert(ignore_permissions=True)


def _equipe(decor: dict) -> None:
    # une équipe ne vise qu'une cible : cours, cohorte ou exercice
    cible = {"cohorte": decor["cohorte"]} if decor["cohorte"] else {"exercice": decor["exercice"]}
    frappe.get_doc({"doctype": "Equipe Correction OpenLab", **cible, "responsable": FORMATEUR,
                    "membres": [{"utilisateur": FORMATEUR, "role": "titulaire"},
                                {"utilisateur": APPRENANTS[3][0], "role": "suppleant"}]}
                   ).insert(ignore_permissions=True)


def _copie(plan: dict, decor: dict) -> str:
    champs = {"doctype": "Copie OpenLab", "soumission": MARQUE + frappe.generate_hash(length=8),
              "apprenant": plan["apprenant"], "exercice": decor["exercice"], "cohorte": decor["cohorte"],
              "type_exercice": TYPE_EXERCICE, "version": 1, "statut": plan["statut"],
              "etape_courante": plan["etape"], "grille_json": decor["grille"], "contenu": CONTENU,
              "depose_le": add_to_date(now_datetime(), days=-3)}
    for champ in ("note", "note_sur", "reussite"):
        if champ in plan:
            champs[champ] = plan[champ]
    if plan.get("souffrance"):
        champs.update(en_souffrance=1, escalade_a=FORMATEUR,
                      souffrance_depuis=add_to_date(now_datetime(), days=-6),
                      echeance=add_to_date(now_datetime(), days=-4))
    return frappe.get_doc(champs).insert(ignore_permissions=True).name


def _proposition(copie: str, source: str, auteur: str, niveaux: dict, confiance=None,
                 commentaires: dict | None = None) -> None:
    frappe.get_doc({"doctype": "Proposition OpenLab", "copie": copie, "source": source, "auteur": auteur,
                    "niveaux_json": json.dumps(niveaux, ensure_ascii=False),
                    "commentaires_json": json.dumps(commentaires or {}, ensure_ascii=False),
                    "confiance": confiance}).insert(ignore_permissions=True)


def _dossier(plan: dict) -> None:
    frappe.get_doc({
        "doctype": "Dossier Paiement OpenLab", "apprenant": plan["apprenant"], "cours": COURS_PAYANT,
        "mode": plan["mode"], "dispense": plan["dispense"], "telephone": "0700000000",
        "date_inscription": add_days(nowdate(), -30), **TARIF,
        "echeances": [{"date_limite": add_days(nowdate(), -5), "montant": 160000,
                       "libelle": "Première tranche"},
                      {"date_limite": add_days(nowdate(), 25), "montant": 160000,
                       "libelle": "Seconde tranche"}],
    }).insert(ignore_permissions=True)


def _versement(plan: dict) -> None:
    dossier = frappe.db.get_value("Dossier Paiement OpenLab",
                                  {"apprenant": plan["apprenant"], "cours": COURS_PAYANT})
    frappe.get_doc({"doctype": "Paiement OpenLab", "dossier": dossier, "montant": plan["montant"],
                    "moyen": plan["moyen"], "reference": MARQUE + frappe.generate_hash(length=6).upper(),
                    "statut": "confirme", "date_paiement": add_to_date(now_datetime(), days=-2),
                    "auteur": FORMATEUR}).insert(ignore_permissions=True)


def run(mot_de_passe: str | None = None) -> dict:
    """Pose le jeu d'essai et rend les identifiants des copies créées, par clé du plan."""
    mdp = mot_de_passe or _mot_de_passe()
    for courriel, prenom, nom in APPRENANTS:
        _utilisateur(courriel, prenom, nom)
    _formateur(mdp)
    _purger()
    _tarif()
    decor = _decor()
    _equipe(decor)

    copies = {}
    for plan in COPIES:
        copie = _copie(plan, decor)
        copies[plan["cle"]] = copie
        if "ia" in plan:
            _proposition(copie, "ia", "ia", plan["ia"], confiance=plan["confiance"],
                         commentaires={"pertinence": "Le besoin est posé avec un client réel."})
            _proposition(copie, "pair", plan["pair"], BON)
        if plan["statut"] == "publiee":
            _proposition(copie, "formateur", FORMATEUR, BON,
                         commentaires={"rigueur": "Pensez à citer vos sources chiffrées la prochaine fois."})

    for plan in RELECTURES:
        frappe.get_doc({"doctype": "Relecture Pair OpenLab", "copie": copies[plan["copie"]],
                        "relecteur": plan["relecteur"], "statut": plan["statut"],
                        "echeance": add_to_date(now_datetime(), days=plan["jours"])}
                       ).insert(ignore_permissions=True)

    for plan in DOSSIERS:
        _dossier(plan)
    for plan in VERSEMENTS:
        _versement(plan)
    frappe.db.commit()

    print(json.dumps({"copies": copies, "exercice": decor["exercice"], "cohorte": decor["cohorte"],
                      "formateur": FORMATEUR, "visiteuse": VISITEUSE}, indent=1, ensure_ascii=False))
    print(f"\nMot de passe du formateur d'essai (banc local, affiché une seule fois) : {mdp}")
    return copies
