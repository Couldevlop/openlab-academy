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
que si elle respecte le schéma JSON et si chaque citation figure dans la copie et compte au moins 8 caractères hors
blancs (sinon le critère est « à revoir »).

Contexte du modèle (réglage « Contexte du modèle (jetons) », `contexte_ia_tokens`, défaut 8192) : le prompt
(consigne, grille, copie) et la réponse doivent tenir dans la fenêtre du serveur. Avant l'appel, le prompt est
estimé (3 caractères par jeton, plus 8 par message) ; s'il dépasse le contexte moins 1024 jetons réservés à la
réponse, la copie n'est ni tronquée ni envoyée : l'étape IA est marquée « non disponible » (« copie trop longue pour
le contexte du modèle ») et la chaîne continue. Avec 8192 jetons, une copie doit rester sous ~20 000 caractères :
régler le plafond de caractères en conséquence ou servir le modèle avec une fenêtre plus grande.

Mesure sur le vrai service, hors suite de tests (rien n'est enregistré) :

```bash
bench --site lms.localhost execute openlab_academy.tests.integration_ia.executer --kwargs "{'nombre': 10}"
```

Fiabilité en continu : API `fiabilite_ia` (écart moyen IA/formateur par critère, superviseurs seulement).

## Paiement des parcours

Chaque parcours a des **frais d'inscription** et trois prix globaux (frais compris) : **en une fois**, **en deux
tranches**, **chaque mois**. Montants en francs CFA (XOF), entiers et **multiples de 5** (contrainte CinetPay). Les
prix sont **figés dans le dossier** de l'apprenant à son inscription : un nouveau tarif ne vaut que pour les
inscriptions suivantes.

### Rôles

| Rôle | Peut |
|---|---|
| **Intendant OpenLab** (économe, créé à l'installation) | saisir les tarifs, voir l'écran Intendance (`/espace/intendance` : filtres, fiche, export Excel), enregistrer un virement, accorder un délai ; lire les réglages de paiement |
| **System Manager** (administrateur) | tout ce que fait l'intendant, plus les réglages de paiement et l'écran Finances (`/espace/finances`, vue résumée) |
| Apprenant | voir et régler son dossier (`/espace/paiement/<parcours>`), choisir ou changer son mode, donner son téléphone |

Donner le rôle : Desk → Utilisateur → Rôles → « Intendant OpenLab ». Toute action d'un agent (virement, délai) et tout
changement de mode d'un apprenant sont journalisés (qui, quoi, quand, avant/après, motif) ; le journal se lit dans la
fiche de l'apprenant, écran Intendance. Les rôles de l'équipe (System Manager, Moderator, Course Creator, Batch
Evaluator, Intendant OpenLab) ne sont jamais bloqués.

### Tarifs (console)

Desk → `/app/tarif-parcours-openlab` → Nouveau : parcours, frais d'inscription, prix en une fois, en deux tranches,
mensuel. Un parcours **sans tarif refuse les inscriptions**. L'intendant choisit le parcours dans la liste (droit
« sélection » seul sur les parcours, accordé à l'installation et à chaque migration).

### Réglages (console « Reglages Paiement OpenLab »)

Desk → `/app/reglages-paiement-openlab` (écriture : System Manager ; lecture : intendant). Les champs secrets sont des
champs mot de passe : chiffrés en base, jamais renvoyés par l'API ni écrits dans un journal ou un message d'erreur.
Laisser une section vide désactive le canal correspondant, sans gêner les autres.

| Section | Champ | Rôle |
|---|---|---|
| CinetPay | Identifiant du site, Clé API, Clé secrète | compte marchand (back-office CinetPay) ; sans eux, le paiement en ligne est masqué et l'apprenant règle par virement |
| CinetPay | URL publique du site (notifications) | adresse HTTPS du site vue d'Internet, ex. `https://academy.openlab.ci/` ; sert aux liens de retour et de notification |
| SMS | URL d'obtention du jeton, Identifiant client, Secret client, Expéditeur | API SMS Orange (OAuth `client_credentials`) ; URL vide = URL Orange par défaut |
| WhatsApp | Identifiant du numéro, Jeton d'accès, Nom du modèle approuvé | WhatsApp Cloud API ; le modèle doit être approuvé par Meta |
| Échéances | Jour d'échéance (1 à 28, défaut 10) ; Rappels (défaut `7,3,1`) ; Inscription refusée après (défaut 2 mois) | calendrier et rappels |
| Virement | Instructions de virement | texte montré tel quel aux apprenants (banque, titulaire, IBAN, motif à indiquer) |

L'e-mail n'a pas de réglage propre : il part par le **compte e-mail sortant par défaut** du site (Desk → Email
Account). Sans compte sortant, le canal e-mail est ignoré.

### Calendrier et blocage

- À l'inscription à une cohorte (`LMS Batch Enrollment`), le dossier s'ouvre en **une fois** : frais dus le jour même,
  le reste le 10 du mois suivant. L'apprenant change de mode sur sa page de paiement ; ce qui est payé reste acquis.
- **Deux tranches** : moitié le 10 du mois suivant l'inscription, moitié le 10 du mois de mi-parcours. **Mensuel** :
  parts égales le 10 de chaque mois jusqu'au mois de fin de cohorte (au moins une).
- Échéance due « au plus tard le 10 » : **en retard dès le 11 à 00:00** (heure d'Abidjan = UTC). Les frais
  d'inscription non réglés bloquent dès l'inscription.
- Un parcours en retard est **bloqué seul** : toute page de ce parcours redirige vers `/espace/paiement/<parcours>`,
  l'API des leçons et des quiz refuse ; les autres parcours à jour restent ouverts. Rien n'est stocké : le blocage
  est recalculé à chaque requête depuis l'échéancier, les paiements confirmés et le délai accordé.
- Déblocage : paiement CinetPay confirmé, virement enregistré par l'intendance, ou **délai** accordé (date limite et
  motif obligatoires).
- Inscription refusée plus de 2 mois après le début de la cohorte (réglable).

### Rappels (tâche de 08:00)

Chaque jour à **08:00** (Abidjan = UTC), l'échéancier Frappe lance `openlab_academy.entrypoints.paiement.envoyer_rappels`
dans la file `long` (une seule exécution à la fois). La tâche revérifie d'abord auprès de CinetPay les paiements en
ligne en attente depuis moins de 7 jours (notification perdue), puis envoie les rappels **7, 3 et 1 jours** avant
chaque échéance, par e-mail, SMS et WhatsApp (chaque canal seulement s'il est configuré). Chaque rappel (J-7, J-3,
J-1) n'est envoyé qu'une fois par échéance et par canal ; il apparaît dans la fiche de l'apprenant. L'échéancier doit être actif
(`bench --site <site> enable-scheduler`) et un worker doit servir la file `long`.

Lancer à la main (sans attendre 08:00) :

```bash
bench --site <site> execute openlab_academy.entrypoints.paiement.envoyer_rappels
```

Les e-mails passent par la file d'envoi de Frappe (Desk → Email Queue).

### Virements

L'apprenant voit les instructions de virement sur sa page de paiement. À réception, l'intendant ouvre la fiche
(`/espace/intendance` → apprenant) → « Enregistrer un virement » : montant, référence (unique), date, motif. Le
virement est confirmé d'office et débloque aussitôt le parcours s'il couvre l'échéance en retard.

### CinetPay : mise en service et essai

1. Créer le compte marchand CinetPay ; dans le back-office, relever l'**identifiant du site**, la **clé API** et la
   **clé secrète** (servant à signer les notifications, en-tête `x-token`).
2. Les saisir dans `/app/reglages-paiement-openlab`, section CinetPay, avec l'**URL publique du site**.
3. URL de notification à déclarer dans le back-office CinetPay (elle est aussi envoyée avec chaque paiement) :
   `https://<site>/api/method/openlab_academy.entrypoints.paiement_api.notification_cinetpay`
   — appel POST de serveur à serveur, sans session ni jeton CSRF : la preuve d'origine est le `x-token`, et le statut
   comme le montant sont toujours relus auprès de `/v2/payment/check` avant toute écriture. Elle répond 200 dans tous
   les cas ; un refus (`REFUSED`) marque le paiement échoué sans ouvrir l'accès. Retour du navigateur :
   `https://<site>/api/method/openlab_academy.entrypoints.paiement_api.retour_cinetpay`.
4. Essai : le site doit être joignable d'Internet en HTTPS (en local, un tunnel HTTPS vers `lms.localhost:8000`).
   Inscrire un apprenant de test, cliquer « Payer <montant> » sur sa page de paiement, régler le plus petit montant que le compte
   accepte (ou utiliser le mode test du compte s'il en propose un), puis vérifier dans la fiche que le paiement passe
   « confirmé » et que le journal porte « paiement_confirme ». Un paiement abandonné reste « en attente » ; il est
   revérifié au retour de l'apprenant et par la tâche de 08:00.
