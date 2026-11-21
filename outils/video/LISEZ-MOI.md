# Les scripts de montage

La chaîne décrite dans [`docs/produire-une-video.md`](../../docs/produire-une-video.md), en trois scripts
qui se lancent chacun seul et affichent ce qu'ils vont faire avant de le faire.

```
captation OBS (.mkv)
   │
   ├─ decouper.py ──────→ séance montée (.mp4), silences retirés, son à −16 LUFS
   │                      + .coupes.json, la liste des coupes, à relire
   │
   ├─ sous_titrer.py ───→ .srt à corriger
   │                      + .relire.md, les passages à vérifier en priorité
   │
   └─ habiller.py ──────→ .habille.mp4 : carton, bandeau, sous-titres, plaque de fin
                          et la valeur à coller dans la clé `video:` de la séance
```

## Ce qu'il faut avoir

| Outil | Pourquoi | Vérifier |
| --- | --- | --- |
| `ffmpeg` | découpe, normalisation, durées | `ffmpeg -version` |
| `whisper-cli` | transcription (whisper.cpp) | `whisper-cli --help` |
| un modèle `ggml-*.bin` | le modèle de transcription | — |
| Node 22+ | l'habillage Remotion | `node -v` |

Sur ce poste, les trois premiers sont installés en portable dans `D:\OPENLAB\outils-bin\`, hors du dépôt,
et ajoutés au PATH utilisateur. L'habillage, lui, demande un `npm install` une fois :

```
cd outils/video/habillage && npm install
```

## Les trois scripts

### 1. Découper

```
python outils/video/decouper.py brut/s01-intro.mkv \
    --vers sorties/00-fondamentaux-data-science/s01-intro.mp4 \
    --reprises brut/reprises.txt --sans-rendu
```

`--sans-rendu` analyse et écrit la liste des coupes sans rien rendre : **relisez-la**, puis relancez sans
l'option. Une découpe automatique se trompe, et une liste corrigée à la main coûte moins cher qu'une prise
refaite.

Le fichier de reprises porte un horodatage par ligne — les endroits où vous avez frappé trois fois sur le
micro avant de reprendre une phrase. Relevez-les sur la forme d'onde : la détection automatique des trois
coups est fragile, un clavier mécanique produit les mêmes pics.

### 2. Sous-titrer

```
python outils/video/sous_titrer.py sorties/00-fondamentaux-data-science/s01-intro.mp4 \
    --modele D:\OPENLAB\outils-bin\modeles\ggml-large-v3-turbo.bin
```

Produit le `.srt` **et** un `.relire.md`. La transcription est une proposition, jamais un livrable.

Le script donne d'abord le lexique du domaine au modèle, ce qui évite le gros des fautes : sans cette
amorce, « Openlab » devient « Zopan Labbé » et « scikit-learn » devient « Sikhi Tlearn ». Ce qui passe
malgré tout est signalé par ressemblance dans le `.relire.md`, avec le mot attendu :

```
- **00:00:06,667** (n° 2) — à vérifier : « LangGraff » → LangGraph ?, « panda » → pandas ?
```

Corrigez le `.srt`, pas le `.relire.md` : il est réécrit à chaque passage.

`--depuis-json` rejoue l'analyse sur une transcription déjà faite, sans relancer le modèle — utile après
avoir enrichi le lexique.

### 3. Habiller

```
python outils/video/habiller.py sorties/00-fondamentaux-data-science/s01-intro.mp4 \
    --titre "Écosystème & méthode" --parcours "Fondamentaux de la Data Science"
```

Le `.srt` voisin est pris automatiquement s'il existe. `--sans-rendu` montre les propriétés sans rendre.

À la fin, le script affiche la ligne à coller dans le fichier de parcours :

```
    video: 00-fondamentaux-data-science/s01-intro.mp4
```

Déposez le fichier sous `sites/<site>/public/files/videos/` **avant** de republier : une vidéo référencée
mais absente fait échouer la publication de ce parcours, exprès.

## Les partis pris

**Python lit, Remotion dessine.** La composition tourne dans un navigateur sans accès au disque. Elle ne
lit donc aucun fichier : les sous-titres lui arrivent déjà analysés, et la durée déjà mesurée. Une
composition qui charge un `.srt` en différé rend une vidéo muette de texte un jour sur dix, sans rien
signaler.

**Tout ce qui décide est pur.** Les 92 tests de `tests/test_montage.py` s'exécutent en une fraction de
seconde, sans captation, sans ffmpeg et sans whisper. Un outil qu'on ne peut éprouver qu'avec un fichier
de 800 Mo sous la main n'est jamais éprouvé. Les appels aux trois programmes extérieurs sont rangés en
bout de chaîne, et ce sont les seules lignes que les tests ne couvrent pas.

**La règle de nommage est écrite deux fois** — dans `domain/parcours.py`, parce qu'un fichier de parcours
la subit, et dans `habiller.py`, parce que cet outil ne peut pas importer Frappe. Un test confronte les
deux : ce que l'outil donne à coller, l'application doit l'accepter. Sans lui, on habille une vidéo qui ne
sera jamais publiable, et on ne s'en aperçoit qu'à la publication.

**Les médias restent dehors.** Captations, rendus et modèles vivent dans `D:\OPENLAB\studio-academy\` et
`D:\OPENLAB\outils-bin\`. Le dépôt ne porte que le code.
