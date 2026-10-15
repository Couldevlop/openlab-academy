"""Rendu des leçons (format Editor.js de Frappe LMS) et des consignes de devoirs.

Toute donnée issue des parcours est échappée : aucun HTML actif ne peut être injecté.
"""
import html
import json

from openlab_academy.domain.parcours import Module, Projet

EXIGENCES_COMMUNES = (
    "README : installation, architecture, choix techniques",
    "Tests automatisés, couverture ≥ 70 %",
    "Lint, formatage et typage vérifiés",
    "CI GitHub Actions verte",
    "Conteneurisé : démarre en une commande",
    "Secrets hors du code (.env.example fourni)",
    "Sécurité OWASP de base",
    "Architecture propre : domaine séparé de l'infrastructure",
    "Commits conventionnels",
    "Décisions documentées (ADR)",
)
GRILLE = (("Fonctionnel", 40), ("Qualité & tests", 25), ("Architecture", 15),
          ("Sécurité", 10), ("Documentation", 10))


def _e(texte: str) -> str:
    return html.escape(texte)


def _bloc(type_: str, **data) -> dict:
    return {"type": type_, "data": data}


def _titre(texte: str) -> dict:
    return _bloc("header", text=texte, level=2)


def _liste(items) -> dict:
    return _bloc("list", style="unordered", items=[_e(i) for i in items])


def _doc(blocks: list[dict]) -> str:
    return json.dumps({"time": 0, "blocks": blocks, "version": "2.29.0"}, ensure_ascii=False)


def lecon_module(module: Module, devoir: str) -> str:
    return _doc([
        _titre("Contenu du module"),
        _bloc("paragraph", text=_e(module.contenu)),
        _bloc("paragraph", text="Format : ~8 h — 40 % théorie, 60 % pratique."),
        _titre("Livrable"),
        _bloc("paragraph", text=f"<b>{_e(module.livrable)}</b>"),
        _bloc("assignment", assignment=devoir),
    ])


def lecon_projet(projet: Projet, devoir: str) -> str:
    return _doc([
        _bloc("paragraph", text=f"<b>{projet.niveau.libelle}</b> · ~{projet.duree_h} h"),
        _titre("Contexte"), _bloc("paragraph", text=_e(projet.contexte)),
        _titre("Objectifs"), _liste(projet.objectifs),
        _titre("Fonctionnalités attendues"), _liste(projet.fonctionnalites),
        _titre("Stack"), _liste(projet.stack),
        _titre("Critères d'acceptation"), _liste(projet.criteres_acceptation),
        _titre("Exigences qualité"), _liste(EXIGENCES_COMMUNES + projet.exigences_specifiques),
        _titre("Livrables"), _liste(projet.livrables),
        _titre("Barème /20"), _liste(f"{nom} : {poids} %" for nom, poids in GRILLE),
        _bloc("assignment", assignment=devoir),
    ])


def consigne_module(module: Module) -> str:
    return f"<p>{_e(module.livrable)}</p><p>Rendez le lien vers votre dépôt Git ou document.</p>"


def consigne_projet(projet: Projet) -> str:
    items = "".join(f"<li>{_e(c)}</li>" for c in projet.criteres_acceptation)
    return (f"<p>Rendez l'URL du dépôt Git de « {_e(projet.titre)} ».</p>"
            f"<p>Critères d'acceptation :</p><ul>{items}</ul>")
