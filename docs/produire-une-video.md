# Produire une vidéo de séance

Guide de production des vidéos de l'académie : ce qu'il faut installer, comment
enregistrer, comment monter, où déposer le résultat. Le format et les décisions qui
l'ont fixé sont dans
[specs/2026-11-18-academy-video-et-notebooks-design.md](specs/2026-11-18-academy-video-et-notebooks-design.md).

## Le format, en une table

| | Durée | Rôle | Ce qu'on y voit |
| --- | --- | --- | --- |
| **Intro de séance** | 2 à 5 min | donner envie et situer | ton visage ou une carte de titre, puis un plan de la séance |
| **Démo d'exécution** | 8 à 12 min | montrer le code qui tourne | l'écran, le terminal, les erreurs comprises |

Une séance porte **une intro** et **une à trois démos**, une par cas d'exécution. Jamais
de captation longue : une vidéo de trois minutes se refait, une de trois heures jamais.

La vidéo **n'est pas la référence** : tout ce qu'elle montre est écrit dans la leçon. Un
apprenant sans son, sans bande passante ou pressé doit pouvoir tout suivre par le texte.
Les sous-titres ne sont donc pas une option.

## Ce qu'il faut installer

Déjà présent sur le poste : Node 22, Python 3.12, et `ffmpeg` + `whisper.cpp` installés
en portable dans `D:\OPENLAB\outils-bin\` (avec le modèle `ggml-large-v3-turbo.bin` sous
`outils-bin\modeles\`). L'habillage porte son propre socle Remotion dans le dépôt
(`outils/video/habillage/`) et demande un `npm install` une fois.

À installer, une fois :

```powershell
# capture d'écran et de voix
winget install --id OBSProject.OBSStudio

# découpe, concaténation, export — le binaire manque dans le PATH
winget install --id Gyan.FFmpeg

# téléchargement des vidéos de référence (pour s'en inspirer, pas pour les recopier)
winget install --id yt-dlp.yt-dlp
```

Fermer et réouvrir le terminal, puis vérifier :

```powershell
ffmpeg -version; yt-dlp --version
```

Les sous-titres passent par `whisper.cpp`, que Remotion installe lui-même ; rien à faire
à la main.

### Ce qui n'est pas nécessaire

- **Claude Desktop** : il n'a pas de terminal, donc il ne peut ni lancer `ffmpeg`, ni
  rendre un projet Remotion, ni déposer un fichier sur le serveur. Et il ne contient
  aucun outil de montage. Tout ce guide se conduit depuis la ligne de commande.
- **Un avatar de synthèse** (HyperFrames et semblables) : la valeur de ces vidéos est que
  c'est toi qui parles, avec tes exemples ivoiriens. Réservé, au plus, à un générique.

## L'atelier

Hors du dépôt — les vidéos pèsent des giga-octets et n'entrent pas dans git :

```
D:\OPENLAB\studio-academy\
├── brut\          captations sorties d'OBS, jamais modifiées
├── references\    vidéos regardées pour s'inspirer de leur rythme
├── images\        cartes de titre, logos, visuels
└── sorties\       vidéos finies, prêtes à publier
```

Le montage, lui, n'est pas là : les trois scripts et le projet Remotion vivent **dans le
dépôt**, sous [`outils/video/`](../outils/video/LISEZ-MOI.md). Seuls les médias restent
dehors.

Règle de nommage, qui décide de tout le reste de la chaîne :

```
<numero-parcours>-<parcours>/s<seance>-intro.mp4
<numero-parcours>-<parcours>/s<seance>-demo-<n>.mp4

01-developpeur-python/s03-intro.mp4
01-developpeur-python/s03-demo-1.mp4
```

C'est ce chemin, exactement, que le YAML du parcours référencera.

## Enregistrer

### Réglages d'OBS, une fois pour toutes

| Réglage | Valeur | Pourquoi |
| --- | --- | --- |
| Résolution de base et de sortie | 1920 × 1080 | le code reste lisible au réencodage |
| Images par seconde | 30 | un screencast n'a pas besoin de 60 |
| Encodeur | x264 (ou NVENC si la carte le permet) | NVENC soulage le processeur |
| Débit | 8000 kb/s en captation | large exprès : on compresse au montage, jamais avant |
| Format d'enregistrement | `mkv` | une coupure de courant ne détruit pas le fichier |
| Fréquence audio | 48 kHz, mono | la voix n'a aucun besoin de stéréo |
| Micro | gain tel que la voix tape vers −12 dB | au-delà, ça sature et rien ne le répare |

Dans la scène : une source **Capture d'écran** et une source **Micro**. Taille de police
de l'éditeur à **18 pt au minimum** — ce qui est confortable sur ton écran est illisible
sur un téléphone.

### Se filmer, ou non

Deux scènes dans OBS, et on bascule de l'une à l'autre selon le moment :

| Scène | Sources | Quand |
| --- | --- | --- |
| **Visage** | Caméra plein cadre + micro | l'intro de séance, et elle seule |
| **Écran** | Capture d'écran + micro, caméra en vignette ou absente | toutes les démos |

On se filme pour l'intro parce qu'un visage engage : l'apprenant décide en vingt
secondes s'il reste, et il le décide devant quelqu'un, pas devant une carte de titre. On
ne se filme pas pendant une démo : la vignette mange un coin de l'écran, et c'est le
code qu'on doit regarder. Si tu n'as pas de caméra, ou pas envie, l'habillage pose une
carte de titre à la place — rien ne casse.

Le cadrage, une fois pour toutes :

| | |
| --- | --- |
| Hauteur de la caméra | **au niveau des yeux**, pas plus bas — une webcam posée sur le bureau filme par en dessous |
| Place dans le cadre | les yeux au tiers supérieur, un poing d'air au-dessus de la tête |
| Distance | à bout de bras : tête et épaules, pas le buste entier |
| Lumière | **face à toi**, pas derrière — une fenêtre dans le dos fait une silhouette noire |
| Fond | ce qu'il y a, rangé. Pas de flou artificiel : il bave sur les contours et fatigue |
| Regard | **l'objectif**, pas ton image à l'écran. Déplace la fenêtre d'aperçu juste sous la caméra |

Le son compte plus que l'image. Un casque-micro à dix centimètres de la bouche bat une
belle caméra avec le micro de l'écran : on pardonne une image moyenne, jamais un son qui
oblige à tendre l'oreille.

### Avant d'appuyer sur enregistrer

- Fermer les notifications, les messageries, les onglets personnels. Une notification
  qui s'affiche, c'est la vidéo à refaire.
- Préparer l'état de départ : le dossier ouvert au bon endroit, le terminal vide, le
  navigateur sur la bonne page.
- Relire les trois phrases d'ouverture à voix haute. Les vingt premières secondes
  décident si on reste.
- Boire de l'eau. Une bouche sèche s'entend.

### Conduite de l'enregistrement

Parle **en une seule prise**, sans chercher la perfection : les hésitations se coupent
au montage, les silences aussi. Ce qui ne se répare pas, c'est un enchaînement faux.
Donc : si tu te trompes, **ne reprends pas depuis le début** — marque la reprise en
tapant trois fois sur le micro (le pic est visible dans la forme d'onde), respire, et
reprends la phrase. Le script de découpe utilise ces repères.

Montre tes erreurs quand elles sont instructives. Un apprenant qui voit une
`TypeError` apparaître, être lue et être corrigée apprend davantage que devant un code
qui marche du premier coup — et il se sentira moins seul devant la sienne.

## Ce qu'on dit

### Une intro de séance, en 3 minutes

| Durée | Contenu |
| --- | --- |
| 0:00 – 0:20 | **La question.** Un problème concret, en une phrase, qui n'a pas encore de réponse. « Ton programme met quarante secondes là où celui du voisin en met deux. Pourquoi ? » |
| 0:20 – 0:50 | **Pourquoi ça compte.** Où ça se paie dans la vraie vie : un entretien, une facture de serveur, un utilisateur qui s'en va. |
| 0:50 – 2:20 | **Le plan.** Les trois ou quatre étapes de la séance, dans l'ordre, chacune en une phrase. Montre l'écran du résultat final — ce qu'on saura faire. |
| 2:20 – 3:00 | **Le contrat.** Ce que tu sauras à la fin, et le livrable qui le prouve. Puis : « le texte de la séance est en dessous, le code aussi ; cette vidéo ne fait que t'ouvrir la porte ». |

Jamais de « bonjour à tous et bienvenue dans cette nouvelle vidéo ». On entre dans le
sujet à la première seconde.

### Une démo d'exécution, en 10 minutes

| Durée | Contenu |
| --- | --- |
| 0:00 – 0:30 | **Ce qu'on va faire tourner**, et l'état de départ visible à l'écran. |
| 0:30 – 7:00 | **On écrit et on exécute**, par petits pas. À chaque pas : l'intention à voix haute **avant** de taper, puis on tape, puis on exécute, puis on lit le résultat. Jamais plus de quarante secondes sans rien exécuter. |
| 7:00 – 9:00 | **Une erreur, volontairement.** Casse quelque chose, lis le message d'erreur à voix haute, explique comment il se lit, répare. C'est la partie que les apprenants revoient. |
| 9:00 – 10:00 | **Ce qui vient ensuite**, et l'exercice à faire maintenant, tout de suite, avant de passer à la suite. |

Dis les noms. « On met ça dans une liste » n'apprend rien ; « on met ça dans une liste,
parce qu'on va avoir besoin de l'ordre, alors qu'un ensemble ne le garderait pas »
apprend quelque chose.

## Monter

La chaîne est en quatre temps, chacun conduit par un script :

1. **Découper et normaliser.** Depuis le `.mkv` brut : les silences longs retirés, les
   reprises coupées aux repères, le son normalisé à −16 LUFS, l'image rendue en `.mp4`
   h264. C'est `ffmpeg` qui travaille ; le script écrit la liste des coupes à côté du
   fichier, pour que tu puisses la relire et la corriger.
2. **Sous-titrer.** `whisper.cpp` transcrit, le résultat est relu **à la main** — un
   modèle automatique écorche les noms propres et le vocabulaire technique, et il n'y a
   pas d'excuse pour publier un sous-titre faux dans un cours.
3. **Habiller.** Le projet Remotion pose la carte de titre, le bandeau du nom de la
   séance, les sous-titres incrustés, les zooms sur la zone de l'écran qui compte, et le
   plan de fin. C'est du code : la même vidéo rendue deux fois donne deux fichiers
   identiques, et refaire une prise ne coûte qu'un rendu.
4. **Publier et vérifier.** La vidéo part sur le serveur sous le chemin de la règle de
   nommage, puis un contrôle relit tous les YAML de parcours et refuse de passer si une
   vidéo référencée est absente — pour qu'aucun apprenant ne tombe sur un lecteur vide.

## Les scripts

Les trois maillons du montage vivent dans [`outils/video/`](../outils/video/LISEZ-MOI.md), avec leur mode
d'emploi :

| | |
| --- | --- |
| `decouper.py` | silences retirés, reprises coupées, son à −16 LUFS, rendu `.mp4` |
| `sous_titrer.py` | transcription whisper.cpp, `.srt` à corriger, liste de relecture guidée |
| `habiller.py` | carton, bandeau, sous-titres, plaque de fin, par Remotion |

Chacun s'exécute seul et affiche ce qu'il va faire avant de le faire. Aucun ne décide à votre place :
`decouper` écrit sa liste de coupes pour que vous la relisiez, `sous_titrer` rend une proposition et la
liste de ce qu'il faut vérifier, `habiller` montre ses propriétés avant de rendre.

## Une séance, de bout en bout

Les quatre commandes, dans l'ordre, telles qu'elles se lancent sur ce poste. Entre
chacune il y a une décision à prendre : c'est là que le travail se fait, pas dans les
commandes.

Prenons la séance 01 du parcours `09-initiation-a-l-ia`, enregistrée sous
`D:\OPENLAB\studio-academy\brut\s01-intro.mkv`.

**1. Voir ce qui serait coupé, sans rien couper.**

```powershell
cd D:\OPENLAB\Openlab_Academy
python outils\video\decouper.py D:\OPENLAB\studio-academy\brut\s01-intro.mkv `
    --vers D:\OPENLAB\studio-academy\sorties\09-initiation-a-l-ia\s01-intro.mp4 `
    --sans-rendu
```

Il annonce ce qu'il garde — « 43,5 s en entrée, 26,1 s gardées en 8 segments » — et écrit
la liste à côté du brut, en `.coupes.json`.

**La décision : le nombre de segments.** Beaucoup de segments courts veut dire qu'il
coupe à l'intérieur de tes phrases, dans les respirations d'une énumération ou d'une
pause d'effet. Remonte alors le seuil et relance l'analyse :

```powershell
... --silence-min 1.2 --sans-rendu
```

Vise un nombre de segments proche du nombre d'idées que tu as développées. Si tu as
marqué des reprises en tapant trois fois sur le micro, relève leurs horodatages sur la
forme d'onde et passe-les avec `--reprises`. Quand la liste te convient, relance **sans**
`--sans-rendu` : c'est le rendu, quelques minutes.

**2. Transcrire.**

```powershell
python outils\video\sous_titrer.py D:\OPENLAB\studio-academy\sorties\09-initiation-a-l-ia\s01-intro.mp4 `
    --modele D:\OPENLAB\outils-bin\modeles\ggml-large-v3-turbo.bin
```

Compte à peu près deux fois la durée de la séance. Il écrit le `.srt` **et** un
`.relire.md`.

**La décision : la relecture.** Ouvre le `.relire.md` : il nomme les passages douteux et,
pour les mots du domaine, propose la correction — « *Ing-Graph* → LangGraph ? ». Corrige
le **`.srt`**, jamais le `.relire.md`, qui est réécrit à chaque passage. Relis aussi ce
qui n'est pas signalé : le modèle se trompe surtout là où il est sûr de lui.

Une fois le `.srt` relu, le script refuse de l'écraser. Si tu enrichis le lexique et
rejoues l'analyse avec `--depuis-json`, il s'arrête et te le dit ; `--ecraser` passe
outre, et tu perds ta relecture.

**3. Habiller.**

```powershell
python outils\video\habiller.py D:\OPENLAB\studio-academy\sorties\09-initiation-a-l-ia\s01-intro.mp4 `
    --titre "L'IA n'est pas un cerveau" --parcours "Initiation à l'IA" --sans-rendu
```

Il affiche les propriétés qu'il passera à Remotion. Vérifie le titre, la mention de
séance et le nombre de répliques lues, puis relance sans `--sans-rendu`.

Si le chemin ne suit pas la règle de nommage, il refuse **avant** de rendre : le dossier
doit porter le numéro du parcours (`09-initiation-a-l-ia`, pas `initiation-a-l-ia`), tiré
du nom du fichier YAML. C'est voulu — sinon on habille une vidéo qui ne sera jamais
publiable, et on s'en aperçoit à la publication.

À la fin, il affiche la ligne à coller dans le YAML.

**4. Déposer, puis publier.**

Le `.habille.mp4` part sur le serveur sous
`sites/<site>/public/files/videos/09-initiation-a-l-ia/s01-intro.mp4`, **avant** de
republier : une vidéo référencée mais absente fait échouer la publication de ce parcours,
exprès. Puis la clé `video:` dans le YAML de la séance, et la republication.

### Si ça coince

| Ce que tu vois | Ce que c'est |
| --- | --- |
| `ne suit pas la règle de nommage` | le dossier n'a pas le numéro du parcours |
| `a été corrigé depuis la transcription` | ta relecture est là et le script la protège : c'est normal |
| `No frame found at position` au rendu | la séance n'a pas été produite par `decouper.py` — repasse-la par lui |
| `aucune parole transcrite` | la piste son est muette : vérifie que le micro était bien dans la scène OBS |

## Rattacher la vidéo à sa séance

Une séance porte sa vidéo par la clé `video:` de son module, dans le YAML du parcours :

```yaml
      - num: "01"
        title: Écosystème & méthode
        video: 00-fondamentaux-data-science/s01-intro.mp4
```

C'est **exactement** le chemin de la règle de nommage ci-dessus. Sur le serveur, il se lit
sous les fichiers publics du site :

```
sites/<site>/public/files/videos/00-fondamentaux-data-science/s01-intro.mp4
                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ce qu'écrit le YAML
```

Publiques, à la différence des archives et des figures : une vidéo se lit en flux, par
intervalles, et le contrôle des médias sert un fichier d'un bloc — une vidéo privée se
téléchargerait donc entièrement avant la première image. Ce n'est pas une fuite : la vidéo ne
montre rien que la leçon ne dise déjà.

Une vidéo hébergée ailleurs s'écrit en adresse complète, **en `https:` seulement** :

```yaml
        video: https://video.openlab.ci/s01-intro.mp4
```

Deux formes, et deux seulement. Tout le reste est refusé à la lecture du fichier : un chemin
absolu, une remontée de dossier, un `.mkv` (le brut de captation, que le navigateur ne lit pas),
une adresse en clair, un `javascript:`.

**Le contrôle.** À la republication, une vidéo référencée mais absente du serveur fait
**échouer ce parcours**, avant toute écriture — le contenu existant n'est pas détruit, et les
autres parcours se publient normalement. Les vidéos manquantes sont toutes nommées dans le même
message : inutile de republier une fois par fichier oublié.

**Qui a le dernier mot.** Sans clé `video:`, une vidéo posée à la main dans l'application reste
en place d'une publication à l'autre — même règle que les retouches. Dès que la clé est écrite,
le fichier de parcours reprend la main.


## Avant de publier, la liste

- [ ] La vidéo tient dans la durée du format.
- [ ] Les vingt premières secondes posent une question, pas une présentation.
- [ ] Le code est lisible : police à 18 pt au moins, zoom là où ça compte.
- [ ] Les sous-titres sont relus, mot à mot.
- [ ] Aucune donnée personnelle, aucune clé d'API, aucun onglet privé à l'écran.
- [ ] Le son ne sature pas et ne force pas à monter le volume.
- [ ] Le texte de la leçon dit tout ce que la vidéo montre.
- [ ] Le fichier respecte la règle de nommage, et le YAML du parcours le référence.
