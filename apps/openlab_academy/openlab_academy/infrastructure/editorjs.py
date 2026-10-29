"""Rendu des leçons (format Editor.js de Frappe LMS) et des consignes de devoirs.

Toute donnée issue des parcours ou des réglages est échappée : aucun HTML actif ne peut être injecté.
"""
import html
import json
import re
from urllib.parse import parse_qs, urlsplit

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


def lecon_module(module: Module, devoir: str, heures: int, quiz: str | None = None,
                 devoir_cas: str | None = None, reglages: Reglages | None = None) -> str:
    blocs = [
        _titre("Contenu du module"),
        _bloc("paragraph", text=_e(module.contenu)),
        _bloc("paragraph", text=f"Format : ~{heures} h — 40 % théorie, 60 % pratique."),
        _titre("Livrable"),
        _bloc("paragraph", text=f"<b>{_e(module.livrable)}</b>"),
        _bloc("assignment", assignment=devoir),
    ]
    if quiz and devoir_cas and reglages:
        blocs += [
            _titre("Exercices"),
            _bloc("paragraph", text=(
                f"Les exercices s'ouvrent {reglages.delai_exercices_minutes} minutes après l'ouverture de la leçon. "
                f"Quiz de {len(module.quiz)} questions : {reglages.score_min} % de bonnes réponses exigé pour valider "
                f"la leçon, {reglages.tentatives_max} tentatives au maximum. Après {reglages.tentatives_max} échecs, "
                "relisez le cours puis demandez à votre formateur de rouvrir le quiz.")),
            _bloc("quiz", quiz=quiz),
            _titre("Mise en situation"),
            _bloc("paragraph", text=_e(module.mise_en_situation)),
            _bloc("assignment", assignment=devoir_cas),
        ]
    return _doc(blocs)


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


def consigne_cas(module: Module) -> str:
    return f"<p>{_e(module.mise_en_situation)}</p><p>Rédigez votre réponse argumentée.</p>"


def consigne_projet(projet: Projet) -> str:
    items = "".join(f"<li>{_e(c)}</li>" for c in projet.criteres_acceptation)
    return (f"<p>Rendez l'URL du dépôt Git de « {_e(projet.titre)} ».</p>"
            f"<p>Critères d'acceptation :</p><ul>{items}</ul>")


# --- vidéo d'une leçon (blocs du format produit par l'éditeur de leçon du LMS) ------------------------------------

_ID_YOUTUBE = re.compile(r"[A-Za-z0-9_-]{11}")
_SEGMENT_VIDEO = re.compile(r"/([A-Za-z0-9_-]{11})")
_SEGMENT_VIMEO = re.compile(r"/([0-9]{1,12})")
_REQUETE_SURE = re.compile(r"[A-Za-z0-9_=&%.-]*")
_FICHIER_LOCAL = re.compile(r"/files/[A-Za-z0-9._~+@/-]+\.((?i:mp4|webm))")
_FICHIER_DISTANT = re.compile(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?/[A-Za-z0-9._~+@/-]+\.((?i:mp4|webm))")
_HOTES_YOUTUBE = {"youtube.com", "www.youtube.com"}
_HOTES_VIMEO = {"vimeo.com", "www.vimeo.com"}


def _integration(service: str, source: str, embed: str) -> dict:
    return _bloc("embed", service=service, source=source, embed=embed, width=580, height=320, caption="")


def _bloc_integration(url: str) -> dict | None:
    """Liste blanche stricte : https, hôtes exacts, identifiant validé ; la source et l'URL d'intégration sont
    reconstruites à partir de l'identifiant, jamais recopiées."""
    try:
        morceaux = urlsplit(url)
        port = morceaux.port
    except ValueError:
        return None
    if not url.startswith("https://") or morceaux.fragment or port is not None or morceaux.username is not None \
            or morceaux.netloc != morceaux.hostname or not _REQUETE_SURE.fullmatch(morceaux.query):
        return None
    hote = morceaux.hostname
    if hote in _HOTES_YOUTUBE and morceaux.path == "/watch":
        ids = parse_qs(morceaux.query).get("v", [])
        identifiant = ids[0] if len(ids) == 1 and _ID_YOUTUBE.fullmatch(ids[0]) else None
    elif hote == "youtu.be":
        trouve = _SEGMENT_VIDEO.fullmatch(morceaux.path)
        identifiant = trouve.group(1) if trouve else None
    elif hote in _HOTES_VIMEO:
        trouve = _SEGMENT_VIMEO.fullmatch(morceaux.path)
        if not trouve or morceaux.query:
            return None
        return _integration("vimeo", f"https://vimeo.com/{trouve.group(1)}",
                            f"https://player.vimeo.com/video/{trouve.group(1)}")
    else:
        return None
    if identifiant is None:
        return None
    return _integration("youtube", f"https://www.youtube.com/watch?v={identifiant}", identifiant)


def bloc_video(url: str | None) -> dict | None:
    """Bloc Editor.js de la vidéo d'une leçon, ou None si le lien n'est pas sûr (javascript:, http:, data:, chemin
    relatif, autre domaine en intégration, caractères inattendus...)."""
    if not isinstance(url, str) or not url:
        return None
    fichier = _FICHIER_LOCAL.fullmatch(url) or _FICHIER_DISTANT.fullmatch(url)
    if fichier:
        if "/../" in url or "/./" in url or url.endswith(("/..", "/.")) or "//" in url.split("://")[-1]:
            return None
        return _bloc("upload", file_url=url, file_type=fichier.group(1).lower(), quizzes=[])
    return _bloc_integration(url)


def avec_video_en_tete(contenu: str | None, bloc: dict | None) -> str | None:
    """Contenu Editor.js (JSON) précédé du bloc vidéo ; contenu illisible ou sans bloc : renvoyé tel quel."""
    if bloc is None:
        return contenu
    if not contenu:
        return _doc([bloc])
    try:
        document = json.loads(contenu)
    except ValueError:
        return contenu
    if not isinstance(document, dict) or not isinstance(document.get("blocks"), list):
        return contenu
    document["blocks"] = [bloc, *document["blocks"]]
    return json.dumps(document, ensure_ascii=False)
