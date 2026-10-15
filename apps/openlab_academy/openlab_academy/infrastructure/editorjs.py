"""Rendu des leçons (format Editor.js de Frappe LMS) et des consignes de devoirs.

Toute donnée issue des parcours ou des réglages est échappée : aucun HTML actif ne peut être injecté.
"""
import html
import json

from openlab_academy.domain.parcours import Module, Projet
from openlab_academy.domain.reglages import Reglages


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


def lecon_module(module: Module, devoir: str, heures: int) -> str:
    return _doc([
        _titre("Contenu du module"),
        _bloc("paragraph", text=_e(module.contenu)),
        _bloc("paragraph", text=f"Format : ~{heures} h — 40 % théorie, 60 % pratique."),
        _titre("Livrable"),
        _bloc("paragraph", text=f"<b>{_e(module.livrable)}</b>"),
        _bloc("assignment", assignment=devoir),
    ])


def lecon_projet(projet: Projet, devoir: str, reglages: Reglages) -> str:
    return _doc([
        _bloc("paragraph", text=f"<b>{projet.niveau.libelle}</b> · ~{projet.duree_h} h"),
        _titre("Contexte"), _bloc("paragraph", text=_e(projet.contexte)),
        _titre("Objectifs"), _liste(projet.objectifs),
        _titre("Fonctionnalités attendues"), _liste(projet.fonctionnalites),
        _titre("Stack"), _liste(projet.stack),
        _titre("Critères d'acceptation"), _liste(projet.criteres_acceptation),
        _titre("Exigences qualité"), _liste(reglages.exigences_communes + projet.exigences_specifiques),
        _titre("Livrables"), _liste(projet.livrables),
        _titre("Barème /20"), _liste(f"{c.nom} : {c.poids} %" for c in reglages.bareme),
        _bloc("assignment", assignment=devoir),
    ])


def consigne_module(module: Module) -> str:
    return f"<p>{_e(module.livrable)}</p><p>Rendez le lien vers votre dépôt Git ou document.</p>"


def consigne_projet(projet: Projet) -> str:
    items = "".join(f"<li>{_e(c)}</li>" for c in projet.criteres_acceptation)
    return (f"<p>Rendez l'URL du dépôt Git de « {_e(projet.titre)} ».</p>"
            f"<p>Critères d'acceptation :</p><ul>{items}</ul>")
