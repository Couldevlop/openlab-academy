#!/usr/bin/env python3
"""Sous-titre une séance montée : transcription par whisper.cpp, découpe en sous-titres lisibles, relecture guidée.

    python outils/video/sous_titrer.py sorties/00-fondamentaux/s01-intro.mp4 --modele modeles/ggml-medium.bin

Deuxième maillon de la chaîne de `docs/produire-une-video.md`. La transcription est **une proposition**,
jamais un livrable : un modèle entraîné sur du français de France écrit « agro-alimentaire » pour
« agroalimentaire », « Abidjan » pour « Abidjan » une fois sur deux, et massacre tout le vocabulaire
technique. Le script produit donc deux fichiers :

- le `.srt`, à corriger ;
- un `.relire.md`, qui liste les passages à vérifier en priorité — les mots du lexique rendus
  autrement qu'attendu, les sous-titres trop longs à lire, et ceux où le modèle a douté.

Sans cette liste, la relecture d'une démo de douze minutes se fait en diagonale, et une erreur passe.

Tout ce qui décide est pur. `whisper.cpp` n'est appelé qu'au début, et il écrit du JSON que ce module relit.
"""
from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

CARACTERES_MAX = 84       # deux lignes de 42 : au-delà, on lit le sous-titre au lieu de regarder l'écran
SECONDES_MAX = 6.0        # un sous-titre qui reste plus longtemps donne l'impression d'un écran figé
SECONDES_MIN = 1.0        # en deçà, l'œil n'a pas le temps : on étire sur le silence qui suit
CARACTERES_PAR_SECONDE = 17.0  # vitesse de lecture confortable en français
CONFIANCE_BASSE = -0.55   # log-probabilité moyenne : en dessous, le modèle a deviné

# Mots que le modèle rend mal et qu'il faut vérifier à chaque fois. Le lexique est du vocabulaire, pas une
# correction automatique : remplacer sans regarder produit des contresens (« agent » n'est pas toujours un
# agent IA).
LEXIQUE = ("Openlab", "Abidjan", "ivoirien", "LangGraph", "Frappe", "Python", "pandas", "scikit-learn",
           "agentique", "LLM", "RAG", "Docker", "Kubernetes", "Git", "SQL", "API", "JSON", "YAML",
           "FCFA", "UEMOA", "Côte d'Ivoire")


@dataclasses.dataclass(frozen=True)
class Replique:
    debut: float
    fin: float
    texte: str
    confiance: float = 0.0

    @property
    def duree(self) -> float:
        return self.fin - self.debut


def lire_whisper(brut: dict) -> tuple[Replique, ...]:
    """Les répliques du JSON de `whisper.cpp` (`--output-json-full`).

    Le format donne les bornes en millisecondes sous `offsets`, et la confiance sous `tokens` quand on a
    demandé le détail. On tolère son absence : une confiance nulle ne déclenche rien, et c'est plus honnête
    que d'inventer une valeur.
    """
    repliques = []
    for segment in brut.get("transcription", ()):
        offsets = segment.get("offsets") or {}
        texte = (segment.get("text") or "").strip()
        if not texte:
            continue
        jetons = [j.get("p", 0.0) for j in segment.get("tokens", ()) if isinstance(j, dict)]
        repliques.append(Replique(
            debut=offsets.get("from", 0) / 1000.0,
            fin=offsets.get("to", 0) / 1000.0,
            texte=texte,
            confiance=(sum(jetons) / len(jetons)) if jetons else 0.0))
    return tuple(repliques)


def _couper_texte(texte: str, maximum: int) -> list[str]:
    """Coupe un texte trop long sur un espace, jamais au milieu d'un mot."""
    morceaux, reste = [], texte.strip()
    while len(reste) > maximum:
        coupe = reste.rfind(" ", 0, maximum + 1)
        if coupe <= 0:  # un seul mot plus long que la limite : on le laisse dépasser plutôt que de le casser
            break
        morceaux.append(reste[:coupe].strip())
        reste = reste[coupe:].strip()
    if reste:
        morceaux.append(reste)
    return morceaux


def fusionner(repliques, caracteres_max: int = CARACTERES_MAX,
              secondes_max: float = SECONDES_MAX) -> tuple[Replique, ...]:
    """Regroupe les répliques en sous-titres lisibles, puis recoupe ce qui reste trop long.

    `whisper.cpp` rend des fragments découpés sur la respiration : « Aujourd'hui », « nous allons voir »,
    « comment un agent décide ». Affichés tels quels, ils clignotent. On les recolle jusqu'à la limite de
    lecture, et on ne recolle **jamais** par-dessus une fin de phrase : un sous-titre qui mélange deux
    phrases se lit deux fois.
    """
    sortie: list[Replique] = []
    for replique in repliques:
        if sortie:
            precedent = sortie[-1]
            ensemble = f"{precedent.texte} {replique.texte}".strip()
            phrase_finie = precedent.texte.endswith((".", "!", "?", "…", ":"))
            if (not phrase_finie and len(ensemble) <= caracteres_max
                    and replique.fin - precedent.debut <= secondes_max):
                sortie[-1] = Replique(precedent.debut, replique.fin, ensemble,
                                      min(precedent.confiance, replique.confiance))
                continue
        sortie.append(replique)

    decoupes: list[Replique] = []
    for replique in sortie:
        morceaux = _couper_texte(replique.texte, caracteres_max)
        if len(morceaux) <= 1:
            decoupes.append(replique)
            continue
        # on répartit la durée au prorata des longueurs : faute de mieux, c'est plus juste qu'à parts égales
        total = sum(len(m) for m in morceaux) or 1
        curseur = replique.debut
        for morceau in morceaux:
            part = replique.duree * len(morceau) / total
            decoupes.append(Replique(curseur, curseur + part, morceau, replique.confiance))
            curseur += part
    return tuple(decoupes)


def _sans_accent(mot: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", mot.casefold())
                   if unicodedata.category(c) != "Mn")


LONGUEUR_RESSEMBLANCE = 6   # en deçà, on exige l'égalité : « RAG » ressemble à « rang », « API » à « api »
# Seuil mesuré, et non choisi : sur les fautes réellement commises par le modèle (« langgraff »,
# « panda », « pyhton », « kubernets », « frape »…) confrontées à deux cents mots de français de cours,
# 0,74 est la valeur la plus basse qui les prenne toutes sans un seul faux positif. À 0,70, « agent » se
# fait prendre pour « agentique ». À 0,82, un tiers des fautes passe.
RESSEMBLANCE = 0.74


def _reduit(mot: str) -> str:
    """Le mot ramené à ses lettres : sans casse, sans accent, sans trait d'union ni espace."""
    return re.sub(r"[^a-z0-9]", "", _sans_accent(mot))


def _mots(texte: str) -> list:
    return re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", texte, re.UNICODE)


def mots_du_lexique_suspects(texte: str, lexique=LEXIQUE) -> tuple[tuple[str, str], ...]:
    """Les passages où un mot du lexique a probablement été écorché : (ce qui est écrit, ce qui est attendu).

    Éprouvé sur une vraie transcription : la version précédente comparait les **orthographes**, si bien
    qu'elle ne voyait que « Open Lab » pour « Openlab ». Or le modèle se trompe par le son — il a écrit
    « LangGraff », « panda », « Sikhi Tlearn » — et elle annonçait zéro passage à relire sur une
    transcription qui en comptait trois. Une liste de relecture vide est pire qu'absente : on la croit.

    On compare donc par ressemblance, sans casse ni accent. Pour les mots courts, on exige l'égalité : à
    trois ou quatre lettres, tout ressemble à tout — « RAG » à « rang », « API » à « api ».

    Ce filet reste le second : le premier est l'amorce donnée au modèle (voir `amorce`), qui empêche la
    faute plutôt que de la rattraper.
    """
    attendus = {_reduit(mot): mot for mot in lexique}
    longs = [cle for cle in attendus if len(cle) >= LONGUEUR_RESSEMBLANCE]
    mots = _mots(texte)
    vus, suspects = set(), []

    def retenir(ecrit: str, attendu: str) -> None:
        if ecrit != attendu and (ecrit, attendu) not in vus:
            vus.add((ecrit, attendu))
            suspects.append((ecrit, attendu))

    for mot in mots:
        nu = _reduit(mot)
        if nu in attendus:
            retenir(mot, attendus[nu])
            continue
        trouves = difflib.get_close_matches(nu, longs, n=1, cutoff=RESSEMBLANCE)
        if trouves:
            retenir(mot, attendus[trouves[0]])

    # Les paires voisines ne servent qu'à rattraper un mot coupé en deux — « Open Lab » pour « Openlab ».
    # On y exige l'égalité des lettres : par ressemblance, « scikit-learn et » passerait pour
    # « scikit-learn », et chaque mot suivant un terme du lexique serait signalé.
    for avant, apres in zip(mots, mots[1:]):
        colle = _reduit(avant) + _reduit(apres)
        if colle in attendus:
            retenir(f"{avant} {apres}", attendus[colle])
    return tuple(suspects)


def a_relire(repliques, confiance_basse: float = CONFIANCE_BASSE,
             vitesse_max: float = CARACTERES_PAR_SECONDE, lexique=LEXIQUE) -> tuple[dict, ...]:
    """Les passages à vérifier, avec la raison. L'ordre est celui de la vidéo : on relit en la regardant."""
    signalements = []
    for i, replique in enumerate(repliques, start=1):
        raisons = []
        if replique.confiance and replique.confiance < confiance_basse:
            raisons.append("le modèle a douté")
        if replique.duree > 0 and len(replique.texte) / replique.duree > vitesse_max:
            raisons.append("trop de texte pour le temps affiché")
        if replique.duree < SECONDES_MIN:
            raisons.append("affiché trop brièvement")
        suspects = mots_du_lexique_suspects(replique.texte, lexique)
        if suspects:
            raisons.append("à vérifier : "
                           + ", ".join(f"« {ecrit} » → {attendu} ?" for ecrit, attendu in suspects))
        if raisons:
            signalements.append({"numero": i, "debut": horodatage(replique.debut),
                                 "texte": replique.texte, "raisons": raisons})
    return tuple(signalements)


def horodatage(secondes: float) -> str:
    """`HH:MM:SS,mmm`, la forme qu'exige le SubRip. Une valeur négative est ramenée à zéro."""
    secondes = max(secondes, 0.0)
    milli = int(round(secondes * 1000))
    heures, reste = divmod(milli, 3_600_000)
    minutes, reste = divmod(reste, 60_000)
    sec, milli = divmod(reste, 1000)
    return f"{heures:02d}:{minutes:02d}:{sec:02d},{milli:03d}"


def en_srt(repliques) -> str:
    """Le fichier SubRip. Les blocs sont numérotés à partir de 1 et séparés par une ligne vide."""
    blocs = []
    for i, replique in enumerate(repliques, start=1):
        lignes = _couper_texte(replique.texte, CARACTERES_MAX // 2)
        blocs.append(f"{i}\n{horodatage(replique.debut)} --> {horodatage(replique.fin)}\n"
                     + "\n".join(lignes[:2]))
    return "\n\n".join(blocs) + "\n"


_BORNES = re.compile(r"(\d\d):(\d\d):(\d\d)[,.](\d{1,3})\s*-->\s*(\d\d):(\d\d):(\d\d)[,.](\d{1,3})")


def _secondes(heures: str, minutes: str, sec: str, milli: str) -> float:
    return int(heures) * 3600 + int(minutes) * 60 + int(sec) + int(milli.ljust(3, "0")) / 1000.0


def lire_srt(texte: str) -> tuple[Replique, ...]:
    """Relit un SubRip, y compris corrigé à la main.

    C'est le fichier que le relecteur a touché : il faut donc tolérer ce qu'un humain y laisse — des
    numéros qui ne se suivent plus après une suppression, un `.` au lieu d'une virgule, des fins de ligne
    de Windows, une ligne vide en trop, un bloc vidé de son texte. On ne tolère pas un bloc sans bornes :
    là, on ne saurait pas quand l'afficher, et le deviner serait pire que de l'ignorer.

    Les lignes d'un même sous-titre sont recollées par une espace : la coupure en deux lignes est une
    décision d'affichage, que l'habillage reprend à sa façon selon la place dont il dispose.
    """
    repliques = []
    for bloc in re.split(r"\r?\n\s*\r?\n", texte.replace("﻿", "")):
        lignes = [ligne.strip() for ligne in bloc.strip().splitlines() if ligne.strip()]
        bornes = next((i for i, ligne in enumerate(lignes) if _BORNES.search(ligne)), None)
        if bornes is None:
            continue
        trouve = _BORNES.search(lignes[bornes])
        corps = " ".join(lignes[bornes + 1:]).strip()
        if not corps:
            continue
        groupes = trouve.groups()
        repliques.append(Replique(_secondes(*groupes[:4]), _secondes(*groupes[4:]), corps))
    return tuple(repliques)


def en_relecture(signalements, total: int) -> str:
    """La liste de relecture, en Markdown : elle se lit à côté de la vidéo."""
    if not signalements:
        return f"# Relecture\n\n{total} sous-titres, rien à signaler. Relisez quand même l'introduction.\n"
    lignes = [f"# Relecture — {len(signalements)} passages sur {total}", "",
              "Corrigez le `.srt`, pas ce fichier : il est réécrit à chaque passage.", ""]
    for s in signalements:
        lignes.append(f"- **{s['debut']}** (n° {s['numero']}) — {' ; '.join(s['raisons'])}")
        lignes.append(f"  > {s['texte']}")
    return "\n".join(lignes) + "\n"


def amorce(lexique=LEXIQUE) -> str:
    """Le lexique donné au modèle **avant** qu'il transcrive, et non vérifié après.

    Éprouvé sur ce poste, sans amorce : « Openlab » est devenu « Zopan Labbé », « LangGraph »
    « Langgraf », « scikit-learn » « Sikhi Tlearn ». Aucun n'a été signalé par `mots_du_lexique_suspects`,
    et c'est normal — il compare des orthographes voisines, alors que le modèle se trompe par le son.
    Rattraper ces fautes après coup demanderait une comparaison phonétique du français, qui se tromperait
    autrement.

    whisper accepte une amorce : quelques phrases qui orientent son vocabulaire. On lui donne donc les
    mots du domaine, dans une phrase plutôt qu'en liste — il la lit comme du contexte, et une énumération
    sèche l'oriente moins bien. `--carry-initial-prompt` la maintient d'un bout à l'autre, faute de quoi
    elle ne porte que sur les trente premières secondes.
    """
    return ("Cours d'Openlab Academy, à Abidjan, en Côte d'Ivoire. On y parle de "
            + ", ".join(lexique) + ".")


# --- le bout qui touche au disque ------------------------------------------------------------------------
def transcrire(source: pathlib.Path, modele: pathlib.Path, langue: str, sortie: pathlib.Path) -> dict:
    """Appelle `whisper.cpp`. Le son est extrait en 16 kHz mono : c'est le seul format qu'il accepte."""
    binaire = shutil.which("whisper-cli") or shutil.which("main")
    ffmpeg = shutil.which("ffmpeg")
    if not binaire:
        raise SystemExit("whisper-cli introuvable : compilez whisper.cpp et mettez-le dans le PATH")
    if not ffmpeg:
        raise SystemExit("ffmpeg introuvable dans le PATH")
    if not modele.is_file():
        raise SystemExit(f"modèle introuvable : {modele}")
    onde = sortie.with_suffix(".16k.wav")
    subprocess.run([ffmpeg, "-hide_banner", "-y", "-i", str(source),
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(onde)], check=True)
    try:
        subprocess.run([binaire, "-m", str(modele), "-f", str(onde), "-l", langue,
                        "--prompt", amorce(), "--carry-initial-prompt",
                        "--output-json-full", "--output-file", str(sortie.with_suffix(""))], check=True)
        return json.loads(sortie.with_suffix(".json").read_text(encoding="utf-8"))
    finally:
        onde.unlink(missing_ok=True)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("source", type=pathlib.Path, help="séance montée (.mp4)")
    a.add_argument("--modele", type=pathlib.Path, required=True, help="modèle ggml de whisper.cpp")
    a.add_argument("--langue", default="fr")
    a.add_argument("--depuis-json", type=pathlib.Path,
                   help="relire un JSON déjà transcrit, sans relancer le modèle")
    args = a.parse_args(argv)

    if args.depuis_json:
        brut = json.loads(args.depuis_json.read_text(encoding="utf-8"))
    else:
        if not args.source.is_file():
            raise SystemExit(f"séance introuvable : {args.source}")
        brut = transcrire(args.source, args.modele, args.langue, args.source)

    repliques = fusionner(lire_whisper(brut))
    if not repliques:
        raise SystemExit("aucune parole transcrite : vérifiez que la séance a bien du son")
    signalements = a_relire(repliques)
    srt = args.source.with_suffix(".srt")
    liste = args.source.with_suffix(".relire.md")
    srt.write_text(en_srt(repliques), encoding="utf-8")
    liste.write_text(en_relecture(signalements, len(repliques)), encoding="utf-8")
    print(f"{len(repliques)} sous-titres écrits dans {srt}")
    print(f"{len(signalements)} passages à relire : {liste}")
    print("La transcription est une proposition. Relisez avant d'habiller.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
