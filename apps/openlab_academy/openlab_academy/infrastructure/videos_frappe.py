"""Vidéos de séance : du chemin écrit dans un parcours à l'adresse servie, et refus si le fichier manque.

Les vidéos ne sont pas livrées avec l'application — une séance pèse des centaines de méga-octets, et un
parcours entier des giga. Elles sont déposées sur le serveur, sous les fichiers publics du site, dans
l'arborescence que `docs/produire-une-video.md` fixe :

    sites/<site>/public/files/videos/06-ia-agentique/s01-intro.mp4
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ce que le parcours écrit

Publiques, à la différence des archives et des figures : une vidéo se lit en flux, par intervalles
(requêtes `Range`), et le contrôle des médias de `entrypoints/lms.py` sert un fichier d'un bloc. Une
vidéo privée se téléchargerait donc entièrement avant la première image. La vidéo ne porte rien que la
leçon ne dise déjà — c'est la règle du format : « la vidéo n'est pas la référence ».

Le contrôle de publication est ici : une vidéo référencée mais absente fait échouer la republication,
plutôt que d'offrir à l'apprenant un lecteur vide.
"""
import pathlib

import frappe

PREFIXE = "/files/videos/"  # adresse publique servie par le site
SOUS_DOSSIER = "videos"


class VideoAbsente(FileNotFoundError):
    """Une vidéo référencée par un parcours n'est pas déposée sur le serveur."""


def racine_par_defaut() -> pathlib.Path:
    """Dossier des vidéos sous les fichiers publics du site."""
    return pathlib.Path(frappe.get_site_path("public", "files", SOUS_DOSSIER))


def _hebergee_ailleurs(video: str) -> bool:
    return video.startswith("https://")


def adresse(video: str, racine: pathlib.Path | None = None) -> str:
    """Adresse à poser dans le champ vidéo de la leçon.

    Une adresse complète passe telle quelle : elle n'est pas la nôtre, on ne peut pas vérifier qu'elle
    existe et on ne prétend pas le faire. Un chemin d'atelier est vérifié sur le disque ; absent, il
    lève `VideoAbsente`.

    Le domaine a déjà refusé les remontées de dossier (`valider_video`). On les rebarre ici : deux
    barrières, comme pour les archives, parce qu'un appelant futur pourrait court-circuiter la première.
    """
    if not video:
        return ""
    if _hebergee_ailleurs(video):
        return video
    dossier = (racine or racine_par_defaut()).resolve()
    fichier = (dossier / video).resolve()
    if not fichier.is_relative_to(dossier) or not fichier.is_file() or fichier.is_symlink():
        raise VideoAbsente(f"vidéo absente du serveur : {video}")
    return PREFIXE + video


def manquantes(videos, racine: pathlib.Path | None = None) -> tuple[str, ...]:
    """Celles qui manquent, toutes nommées d'un coup.

    Une publication qui s'arrête à la première absence oblige à la recommencer autant de fois qu'il
    manque de vidéos. Les adresses hébergées ailleurs et les séances sans vidéo ne comptent pas.
    """
    absentes = []
    for video in videos:
        if not video or _hebergee_ailleurs(video):
            continue
        try:
            adresse(video, racine)
        except VideoAbsente:
            absentes.append(video)
    return tuple(absentes)
