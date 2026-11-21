#!/usr/bin/env python3
"""Découpe et normalise une captation brute : silences retirés, reprises coupées, son à −16 LUFS, rendu .mp4.

    python outils/video/decouper.py brut/s01-intro.mkv --vers sorties/00-fondamentaux/s01-intro.mp4

Premier maillon de la chaîne décrite dans `docs/produire-une-video.md`. Le guide demande d'enregistrer
**en une seule prise**, sans reprendre depuis le début : si on se trompe, on frappe trois fois sur le
micro, on respire, et on reprend la phrase. Ce script lit ces repères.

Il affiche ce qu'il va faire avant de le faire, et écrit la liste des coupes à côté du fichier : une
découpe automatique se trompe, et une liste relue puis corrigée à la main coûte moins cher qu'une prise
refaite.

Tout ce qui décide est pur et se teste sans fichier vidéo ; `ffmpeg` n'est appelé qu'aux deux bouts.
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

# `silencedetect` écrit sur la sortie d'erreur, une ligne par bord de silence
_SILENCE_DEBUT = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_FIN = re.compile(r"silence_end:\s*(-?[\d.]+)")
_DUREE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d\.\d+)")

SEUIL_SILENCE_DB = -32.0  # au-dessus, c'est de la respiration, pas du silence
SILENCE_MIN_S = 0.8       # en deçà, c'est le rythme de la parole : le couper hache le propos
MARGE_S = 0.15            # on laisse respirer de part et d'autre d'une coupe
SEGMENT_MIN_S = 0.4       # un reste plus court qu'un battement de cil ne vaut pas une coupure
LUFS = -16.0              # norme de diffusion parlée


@dataclasses.dataclass(frozen=True)
class Intervalle:
    debut: float
    fin: float

    @property
    def duree(self) -> float:
        return self.fin - self.debut


def lire_silences(journal: str) -> tuple[Intervalle, ...]:
    """Les silences que `ffmpeg -af silencedetect` a trouvés.

    Un silence ouvert à la fin du fichier n'a pas de `silence_end` : il est fermé par la durée, que
    l'appelant connaît. On le laisse ouvert ici (`fin = inf`) pour ne pas inventer une valeur.
    """
    debuts = [float(m) for m in _SILENCE_DEBUT.findall(journal)]
    fins = [float(m) for m in _SILENCE_FIN.findall(journal)]
    silences = []
    for i, debut in enumerate(debuts):
        fin = fins[i] if i < len(fins) else float("inf")
        if fin > debut:
            silences.append(Intervalle(debut, fin))
    return tuple(silences)


def lire_duree(journal: str) -> float:
    """Durée du fichier, lue dans l'en-tête que `ffmpeg` écrit. 0.0 si l'en-tête manque."""
    trouve = _DUREE.search(journal)
    if not trouve:
        return 0.0
    heures, minutes, secondes = trouve.groups()
    return int(heures) * 3600 + int(minutes) * 60 + float(secondes)


def segments_parlants(silences, duree: float, marge: float = MARGE_S,
                      minimum: float = SEGMENT_MIN_S) -> tuple[Intervalle, ...]:
    """Ce qui reste quand on retire les silences, chaque bord rendu de `marge` pour ne pas couper au ras.

    Un segment plus court que `minimum` est abandonné : ce sont des miettes entre deux silences, et les
    garder produit un montage qui hoquette.
    """
    gardes = []
    curseur = 0.0
    for silence in sorted(silences, key=lambda s: s.debut):
        fin = min(silence.debut + marge, duree)
        if fin - curseur >= minimum:
            gardes.append(Intervalle(max(curseur, 0.0), fin))
        curseur = max(curseur, min(silence.fin, duree) - marge)
    if duree - curseur >= minimum:
        gardes.append(Intervalle(curseur, duree))
    return tuple(gardes)


def retirer_reprises(segments, reprises, retour: float = 12.0) -> tuple[Intervalle, ...]:
    """Coupe ce qui précède chaque reprise : la phrase ratée, jusqu'à `retour` secondes en arrière.

    Le repère est un triple coup sur le micro. Ce qui le précède est la phrase que l'orateur vient de
    manquer ; ce qui le suit est la bonne. On ne retire pas plus que `retour` : au-delà, on mangerait du
    propos valable, et personne ne s'en apercevrait avant le rendu.
    """
    resultat = list(segments)
    for marque in sorted(reprises):
        coupe_debut, coupe_fin = marque - retour, marque
        suivant = []
        for segment in resultat:
            if segment.fin <= coupe_debut or segment.debut >= coupe_fin:
                suivant.append(segment)
                continue
            if segment.debut < coupe_debut:
                suivant.append(Intervalle(segment.debut, coupe_debut))
            if segment.fin > coupe_fin:
                suivant.append(Intervalle(coupe_fin, segment.fin))
        resultat = suivant
    return tuple(s for s in resultat if s.duree > 0)


def filtre_de_montage(segments) -> str:
    """Filtre `ffmpeg` qui ne garde que ces segments, image et son ensemble.

    `select` sur l'image, `aselect` sur le son, puis les horodatages refaits (`setpts`, `asetpts`) :
    sans eux le rendu garde les trous et la lecture saute.
    """
    if not segments:
        raise ValueError("aucun segment à garder : la captation est-elle silencieuse de bout en bout ?")
    condition = "+".join(f"between(t,{s.debut:.3f},{s.fin:.3f})" for s in segments)
    return (f"[0:v]select='{condition}',setpts=N/FRAME_RATE/TB[v];"
            f"[0:a]aselect='{condition}',asetpts=N/SR/TB,loudnorm=I={LUFS}:TP=-1.5:LRA=11[a]")


def resume(segments, duree: float) -> dict:
    """Ce que le script annonce avant d'agir, et ce qu'il écrit à côté du fichier."""
    gardee = sum(s.duree for s in segments)
    return {
        "duree_source_s": round(duree, 2),
        "duree_gardee_s": round(gardee, 2),
        "retire_s": round(duree - gardee, 2),
        "part_retiree": round((duree - gardee) / duree, 3) if duree else 0.0,
        "coupes": len(segments),
        "segments": [{"debut": round(s.debut, 3), "fin": round(s.fin, 3)} for s in segments],
    }


# --- les deux bouts, qui touchent au disque --------------------------------------------------------------
def _ffmpeg() -> str:
    chemin = shutil.which("ffmpeg")
    if not chemin:
        raise SystemExit("ffmpeg introuvable dans le PATH : winget install --id Gyan.FFmpeg")
    return chemin


def detecter(source: pathlib.Path, seuil: float, minimum: float) -> str:
    """Passe d'analyse : aucune écriture, seul le journal nous intéresse."""
    sortie = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(source),
         "-af", f"silencedetect=noise={seuil}dB:d={minimum}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return sortie.stderr


def rendre(source: pathlib.Path, vers: pathlib.Path, segments) -> None:
    vers.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_ffmpeg(), "-hide_banner", "-y", "-i", str(source),
         "-filter_complex", filtre_de_montage(segments), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         # 48 kHz explicite : `loudnorm` travaille en interne à 192 kHz et sort à cette fréquence si on
         # ne la fixe pas. C'est du poids pour rien dans une vidéo de cours, et certains lecteurs
         # mobiles rééchantillonnent mal.
         "-c:a", "aac", "-ar", "48000", "-b:a", "160k", str(vers)],
        check=True)


def charger_reprises(chemin: pathlib.Path | None) -> tuple[float, ...]:
    """Repères de reprise relevés à la main, un horodatage en secondes par ligne.

    La détection automatique des trois coups est fragile — un clavier mécanique produit les mêmes pics.
    On relit donc la forme d'onde et on écrit les repères soi-même : c'est long d'une minute, et ça ne
    coupe jamais au mauvais endroit.
    """
    if chemin is None or not chemin.exists():
        return ()
    valeurs = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#")[0].strip()
        if ligne:
            valeurs.append(float(ligne))
    return tuple(valeurs)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("source", type=pathlib.Path, help="captation brute (.mkv sortie d'OBS)")
    a.add_argument("--vers", type=pathlib.Path, required=True, help="fichier .mp4 à écrire")
    a.add_argument("--reprises", type=pathlib.Path, help="fichier d'horodatages de reprise, un par ligne")
    a.add_argument("--seuil", type=float, default=SEUIL_SILENCE_DB)
    a.add_argument("--silence-min", type=float, default=SILENCE_MIN_S)
    a.add_argument("--retour", type=float, default=12.0, help="secondes retirées avant chaque reprise")
    a.add_argument("--sans-rendu", action="store_true", help="analyser et écrire la liste, sans rendre")
    args = a.parse_args(argv)

    if not args.source.is_file():
        raise SystemExit(f"captation introuvable : {args.source}")
    journal = detecter(args.source, args.seuil, args.silence_min)
    duree = lire_duree(journal)
    segments = retirer_reprises(segments_parlants(lire_silences(journal), duree),
                                charger_reprises(args.reprises), args.retour)
    rapport = resume(segments, duree)
    liste = args.source.with_suffix(".coupes.json")
    liste.write_text(json.dumps(rapport, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{args.source.name} : {rapport['duree_source_s']} s en entrée, {rapport['duree_gardee_s']} s "
          f"gardées en {rapport['coupes']} segments "
          f"({rapport['part_retiree']:.0%} retiré). Liste des coupes : {liste}")
    if args.sans_rendu:
        print("Rendu non demandé (--sans-rendu). Relisez la liste, puis relancez sans l'option.")
        return 0
    rendre(args.source, args.vers, segments)
    print(f"Rendu : {args.vers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
