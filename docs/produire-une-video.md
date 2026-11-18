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

Déjà présent sur le poste : Node 22, Python 3.12, et un socle Remotion 4.0.515 éprouvé
dans `D:\OPENLAB\nexusrh-video` (avec `@remotion/captions` et `whisper.cpp` installé).
On réutilise ce socle.

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
├── sorties\       vidéos finies, prêtes à publier
└── montage\       le projet Remotion (habillage, sous-titres, rendu)
```

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

Dans la scène : une source **Capture d'écran** et une source **Micro**. Rien d'autre.
Taille de police de l'éditeur à **18 pt au minimum** — ce qui est confortable sur ton
écran est illisible sur un téléphone.

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

Les scripts vivent dans `studio-academy\montage\scripts\` ; chacun s'exécute seul et
affiche ce qu'il va faire avant de le faire.

## Avant de publier, la liste

- [ ] La vidéo tient dans la durée du format.
- [ ] Les vingt premières secondes posent une question, pas une présentation.
- [ ] Le code est lisible : police à 18 pt au moins, zoom là où ça compte.
- [ ] Les sous-titres sont relus, mot à mot.
- [ ] Aucune donnée personnelle, aucune clé d'API, aucun onglet privé à l'écran.
- [ ] Le son ne sature pas et ne force pas à monter le volume.
- [ ] Le texte de la leçon dit tout ce que la vidéo montre.
- [ ] Le fichier respecte la règle de nommage, et le YAML du parcours le référence.
