#!/usr/bin/env python3
"""Habille une séance montée : carton de titre, bandeau de séance, sous-titres incrustés, plaque de fin.

    python outils/video/habiller.py sorties/00-fondamentaux-data-science/s01-intro.mp4 \
        --titre "Écosystème & méthode" --parcours "Fondamentaux de la Data Science"

Troisième maillon de la chaîne de `docs/produire-une-video.md`. Le rendu est fait par Remotion, dont les
compositions vivent dans `outils/video/habillage/`. Ce script ne dessine rien : il **prépare et vérifie**
les propriétés, puis appelle `remotion render`.

Le nom du fichier porte déjà le parcours, le numéro de séance et la nature de la vidéo (intro ou démo) :
c'est la règle de nommage, et c'est elle qui évite de ressaisir trois fois la même information. Le script
la relit plutôt que de la redemander, et refuse un fichier qui ne la respecte pas — car la même règle décide
de ce que `videos_frappe` saura retrouver au moment de publier. Un fichier mal nommé est un fichier qui
n'arrivera jamais dans un parcours.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import decouper
import sous_titrer

# La règle de nommage, écrite une seconde fois ici parce que cet outil ne peut pas importer l'application
# Frappe. `tests/test_habiller.py` confronte les deux : si l'une change sans l'autre, le test tombe.
NOM = re.compile(r"(?P<parcours>\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)/"
                 r"s(?P<seance>\d{2})-(?P<nature>intro|demo-\d{1,2})\.mp4$")

COMPOSITION = "seance"
RACINE_HABILLAGE = pathlib.Path(__file__).parent / "habillage"
NATURES = {"intro": "Introduction", "demo": "Démonstration"}


class NomHorsRegle(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class Habillage:
    """Ce que la composition Remotion reçoit. Tout est explicite : rien n'est deviné au rendu.

    Les sous-titres arrivent **déjà analysés**. La composition ne lit aucun fichier : elle tourne dans un
    navigateur sans accès au disque, et un `.srt` qu'on y chargerait en différé rendrait la vidéo muette de
    texte un jour sur dix, sans rien signaler. Python lit, Remotion dessine.
    """
    video: str           # nom du fichier seul : le dossier est servi comme dossier public du rendu
    dossier: str         # où ce fichier vit, passé à Remotion et non à la composition
    parcours_dossier: str
    seance: int
    nature: str          # "intro" ou "demo"
    numero_demo: int     # 0 pour une intro
    titre: str
    parcours: str
    sous_titres: tuple = ()  # répliques lues du .srt relu, vide si aucun
    duree: float = 0.0       # durée de la séance, en secondes : Remotion en déduit celle du rendu

    def en_props(self) -> dict:
        return {
            "video": self.video,
            "dureeVideo": round(self.duree, 3),
            "titre": self.titre,
            "parcours": self.parcours,
            "seance": self.seance,
            "nature": self.nature,
            "numeroDemo": self.numero_demo,
            "mention": self.mention(),
            "sousTitres": [{"debut": round(r.debut, 3), "fin": round(r.fin, 3), "texte": r.texte}
                           for r in self.sous_titres],
        }

    def mention(self) -> str:
        """Le bandeau : « Séance 03 · Démonstration 2 » ou « Séance 01 · Introduction »."""
        libelle = NATURES[self.nature]
        if self.nature == "demo":
            libelle = f"{libelle} {self.numero_demo}"
        return f"Séance {self.seance:02d} · {libelle}"


def lire_nom(chemin: pathlib.Path | str) -> dict:
    """Parcours, séance et nature, lus dans le chemin. Lève si le chemin ne suit pas la règle.

    Les séparateurs de Windows sont ramenés à `/` : la règle s'écrit avec des barres obliques, et un
    chemin saisi dans PowerShell en porte des contraires.
    """
    trouve = NOM.search(str(chemin).replace("\\", "/"))
    if not trouve:
        raise NomHorsRegle(
            f"« {chemin} » ne suit pas la règle de nommage de docs/produire-une-video.md : "
            "<numero-parcours>-<parcours>/s<seance>-intro.mp4 ou .../s<seance>-demo-<n>.mp4")
    nature = trouve["nature"]
    return {
        "parcours_dossier": trouve["parcours"],
        "seance": int(trouve["seance"]),
        "nature": "intro" if nature == "intro" else "demo",
        "numero_demo": 0 if nature == "intro" else int(nature.split("-")[1]),
    }


def chemin_de_parcours(chemin: pathlib.Path | str) -> str:
    """Le chemin tel qu'un fichier de parcours doit l'écrire dans sa clé `video:`.

    C'est la sortie utile du script : à la fin du rendu, on connaît la valeur exacte à coller dans le YAML,
    sans la retaper.
    """
    normalise = str(chemin).replace("\\", "/")
    trouve = NOM.search(normalise)
    if not trouve:
        raise NomHorsRegle(f"« {chemin} » ne suit pas la règle de nommage")
    return normalise[trouve.start():]


def titre_par_defaut(parcours_dossier: str) -> str:
    """À défaut de titre donné, le dossier en fait un lisible : « 00-fondamentaux-data-science » devient
    « Fondamentaux data science ». C'est un pis-aller, pas un libellé de production."""
    sans_numero = parcours_dossier.split("-", 1)[1] if "-" in parcours_dossier else parcours_dossier
    return sans_numero.replace("-", " ").capitalize()


def preparer(source: pathlib.Path, titre: str = "", parcours: str = "",
             sous_titres: pathlib.Path | None = None, duree: float = 0.0) -> Habillage:
    """Assemble l'habillage, sous-titres lus et analysés si le fichier est là.

    Le `.srt` attendu est celui que le relecteur a corrigé, pas celui que le modèle a produit : c'est
    pourquoi on le relit depuis le disque à ce moment précis, et non pas depuis la transcription.
    """
    lu = lire_nom(source)
    srt = sous_titres if sous_titres is not None else source.with_suffix(".srt")
    repliques = ()
    if srt and srt.is_file():
        repliques = sous_titrer.lire_srt(srt.read_text(encoding="utf-8"))
    return Habillage(
        video=source.name,
        dossier=str(source.parent.resolve()),
        parcours_dossier=lu["parcours_dossier"],
        seance=lu["seance"],
        nature=lu["nature"],
        numero_demo=lu["numero_demo"],
        titre=titre.strip() or titre_par_defaut(lu["parcours_dossier"]),
        parcours=parcours.strip() or titre_par_defaut(lu["parcours_dossier"]),
        sous_titres=repliques,
        duree=duree)


# --- le bout qui touche au disque ------------------------------------------------------------------------
def duree_video(source: pathlib.Path) -> float:
    """Durée de la séance, lue dans l'en-tête que `ffmpeg` écrit.

    On la lit ici plutôt que dans la composition : sonder la vidéo depuis Remotion demanderait soit un
    navigateur qui ouvre un fichier local, soit `ffprobe` relancé par Node. Les deux marchent un jour sur
    deux ; `ffmpeg -i` sur l'en-tête est instantané et toujours disponible, puisque c'est lui qui a produit
    le fichier.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg introuvable dans le PATH : impossible de connaître la durée de la séance")
    sortie = subprocess.run([ffmpeg, "-hide_banner", "-i", str(source)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    duree = decouper.lire_duree(sortie.stderr)
    if duree <= 0:
        raise SystemExit(f"durée illisible pour {source} : le fichier est-il une vidéo valable ?")
    return duree


def commande_de_rendu(vers: pathlib.Path, props: pathlib.Path, dossier: str,
                      npx: str = "npx") -> list:
    """La commande de rendu. Les propriétés passent par un **fichier**, jamais par la ligne de commande.

    Deux raisons, dans cet ordre. D'abord Windows : `cmd` mutile les guillemets et rend les accents dans
    la page de code du poste, de sorte que Remotion reçoit un JSON invalide — « Écosystème » suffit à
    faire échouer le rendu. Ensuite la longueur : une démonstration de douze minutes porte deux cents
    sous-titres, et la ligne dépasse la limite du système bien avant.

    Remotion recommande lui-même le fichier dans son message d'erreur. On n'attend pas de buter dessus.
    """
    return [npx, "remotion", "render", COMPOSITION, str(vers),
            f"--props={props}", f"--public-dir={dossier}"]


def rendre(habillage: Habillage, vers: pathlib.Path, racine: pathlib.Path = RACINE_HABILLAGE) -> None:
    npx = shutil.which("npx")
    if not npx:
        raise SystemExit("npx introuvable : installez Node 22 ou plus")
    if not (racine / "package.json").is_file():
        raise SystemExit(f"habillage introuvable dans {racine} : lancez d'abord npm install dans ce dossier")
    vers.parent.mkdir(parents=True, exist_ok=True)
    # les propriétés vont dans un dossier temporaire, et non à côté de la séance : le dossier de la séance
    # est servi comme dossier public du rendu, et on n'y ajoute rien qui n'ait à y être.
    with tempfile.TemporaryDirectory() as abri:
        props = pathlib.Path(abri) / "props.json"
        props.write_text(json.dumps(habillage.en_props(), ensure_ascii=False, indent=1), encoding="utf-8")
        subprocess.run(commande_de_rendu(vers, props, habillage.dossier, npx),
                       cwd=str(racine), check=True)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("source", type=pathlib.Path, help="séance montée, nommée selon la règle")
    a.add_argument("--titre", default="", help="titre de la séance, tel qu'il s'affiche au carton")
    a.add_argument("--parcours", default="", help="nom du parcours, tel qu'il s'affiche au bandeau")
    a.add_argument("--sous-titres", type=pathlib.Path, help="fichier .srt (par défaut : à côté de la source)")
    a.add_argument("--vers", type=pathlib.Path, help="fichier à écrire (par défaut : <source>.habille.mp4)")
    a.add_argument("--duree", type=float, default=0.0,
                   help="durée de la séance en secondes (par défaut : lue dans le fichier)")
    a.add_argument("--sans-rendu", action="store_true", help="afficher les propriétés, sans rendre")
    args = a.parse_args(argv)

    if not args.sans_rendu and not args.source.is_file():
        raise SystemExit(f"séance introuvable : {args.source}")
    duree = args.duree or (0.0 if args.sans_rendu else duree_video(args.source))
    try:
        habillage = preparer(args.source, args.titre, args.parcours, args.sous_titres, duree)
    except NomHorsRegle as refus:
        raise SystemExit(str(refus)) from refus

    print(f"{habillage.mention()} — « {habillage.titre} », {habillage.parcours}")
    if habillage.sous_titres:
        print(f"Sous-titres : {len(habillage.sous_titres)} répliques lues")
    else:
        print("Sous-titres : aucun (la séance sera rendue sans texte incrusté)")
    if args.sans_rendu:
        print(json.dumps(habillage.en_props(), ensure_ascii=False, indent=1))
        return 0

    vers = args.vers or args.source.with_suffix(".habille.mp4")
    rendre(habillage, vers)
    print(f"Rendu : {vers}")
    print("À coller dans la clé `video:` de la séance, après avoir déposé le fichier sur le serveur :")
    print("    video: " + chemin_de_parcours(vers if args.vers else args.source))
    return 0


if __name__ == "__main__":
    sys.exit(main())
