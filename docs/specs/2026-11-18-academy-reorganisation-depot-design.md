# Dépôt autonome et outillage d'assistance — conception

Date : 2026-11-18

## Intention

Le projet vit comme sous-dossier d'un monorepo de 122 projets et se publie par
`git subtree split`. Chaque session d'assistance redécouvre l'arborescence, les
commandes et les pièges, puis paie dix minutes de découpage pour publier. L'objet de
ce travail est de rendre le dépôt autonome et d'écrire une fois pour toutes ce qu'il
faut savoir pour y travailler.

## Ce qui coûte aujourd'hui

| Constat | Mesure |
| --- | --- |
| Aucune note de projet (arborescence, commandes, pièges) | tout est redécouvert à chaque session |
| `git status` du monorepo injecté en début de session | 436 lignes, et un parcours de `.avd/` et `.gradle-home/` qui échoue sur un nom de fichier trop long |
| `.git` du monorepo | 221 Mo |
| `git subtree split` pour publier | plus de 10 minutes |
| Permissions pré-accordées | une seule |
| Racine de `docs/` | une trentaine de captures `.PNG`, un `.pptx`, un `.docx`, un `.pdf` en vrac |

## Objectifs

- Publier par un `git push` ordinaire, sans découpage.
- Le savoir nécessaire au projet écrit dans le dépôt, utile à un humain comme à un
  assistant.
- Moins d'invites de permission et moins d'aller-retours pour les gestes répétés.
- Lister `docs/` cesse d'être coûteux.

## Non-objectifs

- Réécrire l'historique : le dépôt distant porte déjà tout l'historique découpé.
- Toucher au contenu pédagogique, au code applicatif ou à la chaîne d'intégration.
- Déplacer les autres projets du monorepo.

## Anti-objectifs

Ce travail est un échec, même s'il fonctionne, si :

- le banc de développement `poc/` perd ses données (le conteneur Frappe n'a pas de
  volume : le recréer efface tout) ;
- un secret local (`credentials-local.md`, `docker/secrets/`) est perdu ou versionné ;
- une trace de l'assistant entre dans le dépôt — fichier, dossier, commit ou PR.

## Contraintes

- `docker-compose` v1, et des piles nommées explicitement (`-p ol-academy`,
  `-p openlab-academy`) : vérification faite, le nom du dossier ne nomme pas les piles.
  Déplacer le dossier ne les casserait donc pas, mais obligerait à recopier à la main
  tout ce que git ne suit pas.
- Mémoire très juste : jamais deux piles Docker en même temps.
- Règle « aucune trace » : rien de nommé d'après l'assistant ne peut être versionné.

## Approches

**1. Cloner dans un nouveau dossier.** Un clone du dépôt distant dans un dossier
dédié, le dossier du monorepo laissé en place. Simple, mais il faut recopier à la main
tout ce que git ne suit pas — `credentials-local.md`, `docker/secrets/`, `poc/`,
`skills-lock.json` — et corriger les chemins dans les notes et les scripts.

**2. Donner son propre `.git` au dossier actuel, sur place** — retenue. Le dossier ne
bouge pas : les scripts, les chemins et les piles Docker restent identiques, et il n'y
a rien à recopier ni aucun secret local à déplacer. Le monorepo cesse de suivre le dossier et l'ignore ; son historique
reste intact. L'arbre local a déjà été vérifié identique à l'arbre publié, donc le
dépôt neuf est propre dès le premier `git status`.

**3. Sous-module git.** Rejetée : tout l'inconfort du monorepo, et un pointeur de
commit à tenir à jour en plus.

*Décision : l'approche 2, variante de ce qui avait été demandé (un clone), parce
qu'elle atteint le même but sans rien déplacer — donc sans recopie de secrets locaux
ni chemin à corriger.*

## Ce qui est mis en place

### Le dépôt

Le dossier `D:\OPENLAB\Openlab_Academy` reçoit son propre dépôt, pointant sur
`github.com/Couldevlop/openlab-academy`, avec tout l'historique distant et le crochet
`pre-push` du dépôt (`core.hooksPath`). Le monorepo cesse de le suivre et l'ignore.
La publication redevient `git push`.

### La note de projet

`docs/CONTRIBUER.md`, versionné, écrit pour un humain qui arrive sur le projet :
arborescence, commandes de test et de vérification, procédure de publication, pièges
(mémoire, `docker-compose` v1, banc de développement sans volume, republication des
parcours), conventions de commit, règles de sécurité et d'architecture, emplacement
des secrets locaux. Un fichier non suivi, exclu par `.gitignore`, y renvoie : c'est le
seul élément nommé d'après l'assistant, et il ne quitte pas le poste.

### Les permissions et les commandes

Dans `.claude/` — non suivi, déjà exclu : une liste de commandes de lecture et de test
pré-accordées, et trois raccourcis pour les gestes répétés (lancer la suite de tests,
lancer la pile de démonstration, publier).

### Le rangement de `docs/`

Les captures partent dans `docs/captures/`, les supports de cours dans
`docs/supports/`. Aucun document versionné n'y renvoie, la vérification a été faite.
Les extensions non encore exclues (`.pptx`, `.pdf`) sont ajoutées à `.gitignore`.

## Laissé à l'exécution

L'ordre des gestes, le détail des permissions pré-accordées, et le découpage exact des
sous-dossiers de `docs/`.
