# openlab_academy

Personnalisation OpenLab Academy pour Frappe LMS : habillage, parcours certifiants, cohortes.

## Développement

Banc de dev : conteneur `openlab-academy_frappe_1` (bench `/home/frappe/frappe-bench`, site `lms.localhost`).

```bash
bash docker/dev-sync.sh                     # copie l'app dans le bench
bench --site lms.localhost install-app openlab_academy
bench --site lms.localhost run-tests --app openlab_academy
```

## Architecture (Clean Architecture / DDD)

| Couche | Dossier | Rôle |
|---|---|---|
| Domaine | `domain/` | Entités `Parcours`, `Projet`, `Module` ; invariants ; plan des chapitres. Aucune dépendance. |
| Application | `application/` | Cas d'usage `PublierParcours` ; port `DepotCatalogue`. |
| Infrastructure | `infrastructure/` | Source YAML (`yaml_source`), rendu Editor.js (`editorjs`), adaptateur Frappe LMS (`depot_frappe`). |
| Entrée | `entrypoints/` | Commandes `bench execute` (racine de composition). |

Données : `data/parcours/*.yaml` (un fichier par parcours, 10 projets + 1 capstone obligatoires).

```bash
bash docker/dev-test.sh                     # tous les tests + couverture (seuil 99 %)
bench --site lms.localhost execute openlab_academy.entrypoints.seed.run
```

## Exploitation (image Docker)

```bash
cd docker
cp .env.example .env            # puis remplacer les mots de passe
docker-compose -p ol-academy build
docker-compose -p ol-academy up -d
```

- Premier démarrage : création du site `SITE_NAME`, installation de payments, lms et openlab_academy
  (réglages fr / Africa/Abidjan / XOF, publication des parcours, cohorte pilote standard).
- Redémarrages suivants : `bench migrate`, aucune recréation ; données dans les volumes `sites` et `mariadb-data`.
- Ouvrir une cohorte intensive (16 h/semaine) :
  `docker exec ol-academy_app_1 bench --site <site> execute openlab_academy.entrypoints.cohorte.ouvrir_pilote --kwargs "{'rythme': 'intensif'}"`
- Ajouter ou modifier un parcours : éditer `data/parcours/NN-<slug>.yaml` (10 projets + 1 capstone obligatoires),
  reconstruire l'image, puis `bench --site <site> execute openlab_academy.entrypoints.seed.run`.
  Un cours qui a déjà des inscrits n'est jamais modifié.

## Réglages (écran « Reglages OpenLab Academy »)

Desk → `/app/reglages-openlab-academy` (System Manager uniquement). Tout réglage incohérent est refusé à l'enregistrement.

| Section | Réglages |
|---|---|
| Pédagogie | projets par portfolio, heures par module, délai et jour d'ouverture des cohortes |
| Barème | critères et poids (total 100 %) |
| Exigences qualité | textes ajoutés à chaque énoncé de projet |
| Rythmes | code, libellé, heures du lundi au dimanche (ex. standard 12 h, intensif 16 h, week-end…) |
| Séances | heures de début et de fin, fuseau |
| Cohorte pilote | parcours, formateur par défaut |
| Plateforme | nom, logo, langue, devise |

Un parcours peut surcharger `projets_par_portfolio` et `heures_par_module` dans son YAML (`parametres:`).
Les changements s'appliquent aux prochaines publications et cohortes, jamais rétroactivement.

## Parcours « à venir »

Un fichier de parcours avec `statut: a_venir` ne contient que la carte (titre, accroche, description, tags,
couleur) : le cours est publié en « Upcoming », sans leçon. Remplacer le fichier par le parcours complet
(sans `statut`) le publie entièrement à la relance du seed. Cas actuel : Ingénieur Cybersécurité I et II
(modèles à compléter dans `docs/modeles/`).

## Exercices de fin de leçon

Chaque module du YAML porte `quiz` (questions : `question`, `options`, `bonnes` numérotées à partir de 1,
`explication`) et `mise_en_situation`. Nombre de questions, tentatives, score exigé et délai de déblocage
se règlent dans l'écran de réglages. Le délai est vérifié côté serveur à chaque soumission.

## Évaluation des copies (console, réglages, IA)

Chaque rendu d'un devoir LMS (`LMS Assignment Submission`) devient une copie OpenLab qui suit sa chaîne :
auto-évaluation → contrôles automatiques → pré-correction IA → pairs → jury → formateur, chaque étape activable.
Rien ne bloque : une étape indisponible ou échue applique l'action réglée (passer, réattribuer, escalader,
dispenser) ; la tâche horaire `traiter_echeances` s'en charge. Seul un humain publie une note définitive.

**Écrans** (`/espace`, connexion requise) : relecture par les pairs (`/espace/relecture`), correcteur
(`/espace/correcteur`, touches 1 à 4, J/K), lots (`/espace/lots`), retour de l'apprenant (`/espace/retour/<copie>`,
lien écrit dans le commentaire de la soumission LMS à la publication).

**Console** (bureau Frappe, System Manager ; lecture pour le rôle « Responsable pédagogique OpenLab ») :

| Écran | Réglages |
|---|---|
| `/app/reglages-evaluation-openlab` | étapes par type d'exercice (actif, délai, action à expiration), paramètres par type (nombre de pairs, anonymat, note masquée avant relectures, note sur N, seuil), publication provisoire, responsable pédagogique, IA, hôtes de dépôts et jeton, longueur minimale, grille générique |
| `/app/surcharge-evaluation-openlab` | surcharge par cohorte ou par exercice : chaîne complète, suppléant du formateur |
| `/app/delegation-openlab` | délégations en cours (titulaire, délégataire, période, cohorte ou exercice) ; aussi par l'API `deleguer` |

Priorité : surcharge exercice > surcharge cohorte > YAML de l'exercice > type d'exercice > défauts du code ;
la republication des parcours n'écrase jamais la console.

**IA** (section IA de la console) : URL d'un service compatible OpenAI (`/v1/chat/completions` : llama.cpp
server, Ollama, vLLM), modèle pour les copies texte et pour les rendus en URL, clé (champ mot de passe, vide si le
service n'en demande pas), délai max par copie (minutes), seuil de confiance des lots, plafond de caractères de
l'instantané, tournures d'injection. La clé ne part jamais en HTTP clair vers un hôte public (HTTPS exigé) ; aucune
redirection n'est suivie. La pré-correction tourne dans la file `long` de RQ, une copie à la fois. Une copie qui
contient une tournure d'injection n'est pas envoyée : elle est signalée au formateur. La réponse n'est retenue
que si elle respecte le schéma JSON et si chaque citation figure dans la copie (sinon le critère est « à revoir »).

Contexte du modèle : le prompt (consigne, grille, copie) et la réponse doivent tenir dans la fenêtre du serveur.
Avec une fenêtre de 4096 jetons, une copie doit rester sous ~8 000 caractères (≈ 3,2 caractères par jeton en
français) : régler le plafond de caractères en conséquence ou servir le modèle avec une fenêtre plus grande.
Au-delà, le service répond HTTP 400 et l'étape IA est marquée « non disponible ».

Mesure sur le vrai service, hors suite de tests (rien n'est enregistré) :

```bash
bench --site lms.localhost execute openlab_academy.tests.integration_ia.executer --kwargs "{'nombre': 10}"
```

Fiabilité en continu : API `fiabilite_ia` (écart moyen IA/formateur par critère, superviseurs seulement).
