# Vidéos de séance et notebooks exécutables — conception

Date : 2026-11-18

## Intention

Les parcours promettent « en vidéo, à votre rythme » et livrent du texte. Les notebooks
du fil rouge se téléchargent en archive, donc rien ne s'exécute avant que l'apprenant
ait installé Python chez lui — et c'est là que les abandons commencent. L'objet de ce
travail est de donner à chaque séance une vidéo courte et à chaque notebook la
possibilité de tourner dans le navigateur, sur le modèle de ce que font
DeepLearning.AI et OpenClassrooms.

## Ce qui existe déjà, et ce qui manque

Vérifié dans le code avant d'écrire une ligne :

| Brique | État |
| --- | --- |
| Lecteur vidéo d'une leçon | **fait** : `CHAMP_VIDEO` sur `Course Lesson`, inséré en tête de leçon par `get_lesson`, testé (`test_video_lecon_frappe.py`) |
| Liens acceptés | **fait et large** : YouTube, Vimeo, **et fichiers auto-hébergés** `/files/….mp4` ou `https://hôte/….mp4|webm` — validation stricte dans `bloc_video` (pas de `../`, pas de port, extension contrôlée, identifiants reconstruits) |
| Déclarer la vidéo d'une séance dans la source de vérité | **manque** : le champ ne se remplit qu'à la main dans l'interface, insoutenable sur 277 sections |
| Poser une vidéo au milieu d'une leçon | **manque** : le domaine a `Figure`, `Tableau`, `Extrait` comme supports d'une section ; il n'a pas `Video` |
| Notebooks | **archive `.zip`** construite par `construire_notebooks.py` depuis `cellules.py`, servie depuis `data/ressources/` — à télécharger |
| Chaîne de montage | **déjà possédée** : quatre projets Remotion 4.0.515 sur ce poste (`nexusrh-video`, `maturia-video`, `opencacao/video`, `OFI_Video`), dont un avec `@remotion/install-whisper-cpp`, `@remotion/captions` et `whisper.cpp/` installé |
| `ffmpeg`, `yt-dlp` | absents du `PATH` (Remotion embarque le sien, les scripts de découpe ont besoin du binaire) |

## Objectifs

- Une vidéo d'introduction par séance, déclarée dans le YAML du parcours.
- Des vidéos de démonstration posées à l'endroit exact de la leçon qu'elles montrent.
- Les notebooks exécutables dans le navigateur partout où c'est techniquement possible.
- Une chaîne de production et de montage reproductible, pilotée par des scripts.

## Non-objectifs

- Remplacer le texte par la vidéo : le texte reste la référence, la vidéo l'introduit
  et montre. Un apprenant sourd ou en bande passante faible doit pouvoir tout suivre.
- Une voix de synthèse. La voix est celle de l'auteur ; c'est un parti pris du projet.
- Héberger les vidéos dans git.

## Anti-objectifs

Échec, même si tout fonctionne, si :

- une vidéo devient obligatoire pour réussir une séance ;
- le dépôt grossit de plusieurs giga-octets ;
- une leçon référence une vidéo absente du serveur, et l'apprenant tombe sur un
  lecteur vide ;
- l'exécution dans le navigateur donne une fausse impression de maîtrise, en masquant
  l'installation locale que le métier exige de toute façon.

## Contraintes

- Nœud unique, mémoire très juste. Servir des fichiers statiques par nginx ne coûte pas
  de mémoire, mais occupe du disque et de la bande passante.
- `docker-compose` v1, piles nommées par `-p`.
- Souveraineté : l'hébergement par défaut est celui d'OpenLab.
- Aucune trace d'assistant dans le dépôt.

## Format retenu

Sur le modèle d'OpenClassrooms, deux formats courts plutôt qu'une captation longue :

| | Durée | Rôle | Poids (1080p, screencast, ~1,2 Mb/s) |
| --- | --- | --- | --- |
| Intro de séance | 2 à 5 min | ce que tu vas faire, pourquoi ça compte, ce que tu sauras à la fin | ~45 Mo |
| Démo d'exécution | 8 à 12 min | on tape le code et on le voit tourner, erreurs comprises | ~90 Mo |

Une séance porte une intro et, selon les cas d'exécution, une à trois démos :
~225 Mo par séance, **~4 Go par parcours de dix-huit séances**, ~32 Go pour les huit
parcours. À comparer à 1,5 Go pour **une seule** séance captée en trois heures. Le
motif décisif n'est pas le poids : une vidéo de trois minutes se refait en vingt
minutes, une de trois heures ne se refait jamais.

## Approches de l'hébergement

**1. YouTube non répertorié.** Zéro bande passante, lecture fluide en Afrique de
l'Ouest, code déjà prêt. Mais une académie qui enseigne la souveraineté numérique en
confiant ses cours à Google s'expose à la seule critique qui compte, et YouTube peut
retirer une vidéo sans recours.

**2. Auto-hébergé sur l'infrastructure OpenLab** — retenue. `bloc_video` accepte déjà
les fichiers `.mp4` et `.webm` : aucun lecteur à écrire. nginx sert les fichiers avec
les requêtes par intervalles, donc le déplacement dans la barre de lecture fonctionne.
32 Go de disque et quelques centaines de giga-octets de transfert par mois restent dans
l'épure d'un serveur Hetzner.

**3. Les deux selon le parcours.** Rejetée pour l'instant : deux chemins à maintenir
pour un gain hypothétique. À reprendre si le transfert devient un problème mesuré.

*Décision : auto-hébergé, avec repli YouTube possible sans changement de code puisque
les deux formes de lien passent par le même champ.*

## Approches des notebooks

**1. JupyterLite, exécution dans le navigateur** (Pyodide, aucun serveur) — retenue,
avec un périmètre. Servi en fichiers statiques par l'application Frappe, il fonctionne
hors ligne une fois chargé et ne coûte rien au serveur. `numpy`, `pandas`,
`matplotlib`, `scikit-learn` y tournent : **Développeur Python, Fondamentaux de la Data
Science et Python pour les RH y passent entièrement**. Le parcours IA agentique, lui,
appelle le réseau, LangChain, LangGraph et MCP : **il ne peut pas y tourner**, il garde
son archive et une phrase qui explique pourquoi — l'installation locale fait partie du
métier qu'il enseigne.

**2. Un serveur Jupyter par apprenant.** Rejetée : un nœud unique déjà à l'étroit ne
porte pas un noyau Python par apprenant.

**3. Garder le téléchargement seul.** Rejetée : c'est la marche à laquelle les
apprenants s'arrêtent.

## Ce qui sera construit

### Dans l'application

1. **Clé `video:` sur une séance** du YAML de parcours, chemin relatif
   (`06-ia-agentique/s01-intro.mp4`) ou URL complète. Le dépôt la pose dans
   `CHAMP_VIDEO` à la republication ; le lecteur existant fait le reste.
2. **Support `Video` sur une section**, au même patron que `Figure` : dataclass validée
   dans le domaine, rendu par `bloc_video` dans `editorjs.py`, posé au plus près du
   texte qu'il montre.
3. **Un contrôle de cohérence** : une vidéo référencée mais absente du serveur fait
   échouer la republication plutôt que d'offrir un lecteur vide. Même esprit que le
   contrôle des archives du fil rouge.
4. **JupyterLite** construit en fichiers statiques dans `public/labo/`, avec les
   notebooks du parcours préchargés, et un lien « ouvrir dans le navigateur » à côté du
   lien de téléchargement — affiché seulement pour les parcours dont le périmètre le
   permet.

### Hors de l'application

5. **Un atelier de production** à côté du dépôt, pas dedans : `brut/` (captations),
   `references/` (vidéos regardées pour s'en inspirer), `images/` (visuels),
   `sorties/` (vidéos finies), et un projet Remotion pour l'habillage.
6. **Les scripts** : découper et normaliser une captation, générer les sous-titres,
   habiller par Remotion, rendre, puis publier sur le serveur et vérifier que chaque
   vidéo référencée existe bien.

Le guide de production — réglages d'OBS, structure d'une intro, d'une démo, conduite de
l'enregistrement, montage — est dans [produire-une-video.md](../produire-une-video.md).

## Ma méthode de travail

Le partage est simple : **tu enregistres, le reste est écrit en code.** Tu fournis la
captation d'écran et la voix ; découpe, sous-titres, habillage, rendu, publication et
vérification sont des scripts, donc rejouables à l'identique quand tu refais une prise.

Sur l'outillage que tu as vu décrit ailleurs, trois mises au point :

- **Claude Desktop n'est pas nécessaire, et serait un recul ici.** Il n'a pas de
  terminal : il ne peut ni lancer `ffmpeg`, ni rendre un projet Remotion, ni pousser sur
  le serveur. C'est la ligne de commande qui fait ce travail, et c'est là que nous
  sommes déjà. Aucun outil de montage vidéo n'existe dans Claude Desktop.
- **Remotion, Whisper et `ffmpeg` : tu les possèdes déjà.** `nexusrh-video` tourne en
  Remotion 4.0.515 avec `@remotion/captions` et `whisper.cpp` installé, et une chaîne
  `caler → rendre` qui fonctionne. On réutilise ce socle au lieu d'en inventer un
  deuxième. `ffmpeg` manque seulement dans le `PATH` ; `yt-dlp` reste à installer, pour
  les références uniquement.
- **HyperFrames ne sert pas le cœur du sujet.** Il fabrique des plans et des avatars de
  synthèse. Or la valeur de ces vidéos est que c'est toi qui parles, avec ton accent et
  tes exemples ivoiriens. Il peut servir à un générique ou à un plan d'illustration, pas
  à enseigner. Non retenu au départ ; rien n'empêche de l'ajouter ensuite.

Les vidéos de référence se regardent pour apprendre leur rythme et leur découpage.
Elles ne se recopient pas : ni extrait, ni visuel, ni musique.

### Recette dans le navigateur

Chaque ajout est vérifié dans Chrome sur la pile de démonstration, pas seulement par
les tests : le lecteur apparaît en tête de leçon, la barre de lecture se déplace
(requêtes par intervalles), une démo s'affiche au bon endroit dans la leçon, les
sous-titres s'activent, et dans le laboratoire une cellule `pandas` s'exécute et rend
son résultat. Le rendu à 375 px de large est contrôlé dans la même passe — il restait
en souffrance.

## Laissé à l'exécution

L'ordre des lots, le nom exact des clés YAML, le découpage des scripts, et la version
de JupyterLite épinglée.
