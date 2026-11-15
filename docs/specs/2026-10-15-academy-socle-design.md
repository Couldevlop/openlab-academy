# OpenLab Academy — Sous-projet 1 : socle

Date : 2026-10-15 · Branche : `feat/academy-socle` (monorepo `D:\OPENLAB`)

## 1. Intention

Plateforme de formation certifiante d'Openlab Consulting pour un public ivoirien et ouest-africain.
Modèle pédagogique : cohortes, modules hebdomadaires ~8 h (40 % théorie / 60 % pratique), un livrable
corrigé par module, projet fil rouge devant jury (cf. `OpenLab_Academy_Catalogue.docx`).

Décisions validées :
- Base : **Frappe LMS** (v15) auto-hébergé, prototype validé en local (`poc/`).
- Personnalisation par **app Frappe séparée `openlab_academy`** — aucun fork de LMS.
- Paiement futur : **CinetPay** (sous-projet 2).
- Code dans le monorepo, dossier `Openlab_Academy/`.

Découpage global : 1. socle (ce document) · 2. paiement CinetPay XOF · 3. déploiement Hetzner · 4. labs (JupyterHub, Judge0, CTFd).

## 2. Périmètre du socle

Inclus :
1. App `openlab_academy` installable sur un site Frappe v15 portant `payments` + `lms`.
2. Habillage OpenLab.
3. Seed idempotent des 5 parcours du catalogue.
4. Un devoir (LMS Assignment) par livrable de module.
4bis. **Portfolio par parcours : 10 projets complets + 1 capstone** (55 projets au total), en plus des
   livrables hebdomadaires (cf. §4.3).
5. Une cohorte pilote.
6. Image Docker figée + compose reproductible.

Exclus : paiement, déploiement, labs, vitrine SEO, notifications WhatsApp.

## 3. Structure

```
Openlab_Academy/
  apps/openlab_academy/
    openlab_academy/
      hooks.py                 # app_include_css, after_install, fixtures
      install.py               # after_install : réglages + seed
      seed/
        parcours.yaml          # source des 5 parcours (données pures)
        loader.py              # YAML -> cours/chapitres/leçons/devoirs (idempotent)
      public/css/openlab.css   # tokens + surcharges UI LMS
      public/images/logo.svg
      tests/test_seed.py
    pyproject.toml
  docker/
    Dockerfile                 # frappe/bench v15 + payments + lms + openlab_academy, assets buildés
    docker-compose.yml         # format v1 compatible (pas de `name:`, pas de `profiles:`)
    entrypoint.sh              # crée le site au 1er démarrage, sinon démarre
    .env.example
  docs/specs/
```
`poc/` est supprimé une fois le socle fonctionnel.

## 4. Composants

### 4.1 Habillage
- Tokens issus de `openlabconsulting/docs/reference/brand-identity.md` : orange `#ff5a00`
  (accent, < 15 % de surface), navy `#0b1b3d`, night `#0a0e1a`, ivory `#faf8f5` ; polices Geist (corps),
  Bricolage Grotesque (titres), JetBrains Mono (code).
- Injection via `app_include_css` / `web_include_css` ; surcharge des variables CSS de frappe-ui.
- Réglages appliqués à l'installation : `LMS Settings` (logo, nom « OpenLab Academy »),
  `System Settings` (langue `fr`, fuseau `Africa/Abidjan`, devise `XOF`, format date `dd-mm-yyyy`).

### 4.2 Seed des parcours
- `parcours.yaml` : liste de parcours → `title`, `short_introduction`, `description`, `tags`,
  `blocs[]` → `title`, `modules[]` → `title`, `contenu`, `livrable` ; plus `projet_final`.
  Contenu extrait du catalogue (5 parcours : Fondamentaux Data Science, Développeur Python,
  AI Engineer, Data Engineer, Ingénieur Cybersécurité).
- Les fourchettes de rémunération en k€ du catalogue **ne sont pas reprises**.
- Chaque bloc → `Course Chapter` ; chaque module → `Course Lesson` (contenu Editor.js :
  contenu, format, livrable) ; projet final → dernier chapitre.
- Chaque livrable → `LMS Assignment` (type « URL » ou « Document ») rattaché à la leçon via
  la table `assessments`.
- Idempotence par clé naturelle (titre du cours) : met à jour l'existant au lieu de dupliquer ;
  ne supprime jamais un cours portant des inscriptions.
- Lancement : `after_install` + commande `bench --site X execute openlab_academy.seed.loader.run`.

### 4.3 Portfolio de projets
Chaque parcours = modules hebdomadaires (livrables courts) **+ 10 projets portfolio + 1 capstone**.
Le capstone remplace le « projet final fil rouge » du catalogue. Durée du parcours allongée d'environ 50 %.

Placement : les projets sont intercalés en « semaines projet » après les modules qu'ils consolident
(champ `apres_module`), ~12 h chacun ; le capstone (~3 semaines) clôt le parcours. Dans LMS : un chapitre
« Projet N — … » contenant une leçon d'énoncé + un `LMS Assignment` (rendu = URL du dépôt Git).

Fiche projet (`portfolio[]` dans `parcours.yaml`, validée au chargement) :
- `titre`, `apres_module`, `duree_h`
- `contexte` — cas d'usage réel ouest-africain (Mobile Money, cacao, transport Abidjan, santé, PME, administration…)
- `objectifs`, `fonctionnalites` (périmètre fonctionnel complet, pas un exercice)
- `stack` — outils actuels du métier en 2026 (ex. Python : uv, ruff, mypy/pyright, Pydantic v2, FastAPI, pytest ;
  Data : Polars, DuckDB, dbt, Dagster/Airflow, Parquet/Iceberg ; IA : SDK LLM, sorties structurées, RAG hybride,
  MCP, LangGraph, evals ; Cyber : OWASP Top 10/ASVS, SAST/DAST, détection Sigma, IaC sécurisée)
- `criteres_acceptation` — vérifiables, dont : démarre avec une commande (`docker compose up` ou équivalent),
  tests verts, démo fonctionnelle
- `exigences_qualite` — socle commun à tous les projets, complété par parcours :
  README (installation, architecture, choix), tests automatisés (couverture ≥ 70 %), lint + format + typage,
  CI (GitHub Actions) verte, conteneurisation, secrets hors du code (`.env.example`), sécurité OWASP de base,
  architecture propre (séparation domaine / infra), commits conventionnels, journal de décisions (ADR)
- `livrables` — dépôt Git, démo (déployée ou vidéo ≤ 3 min), rapport court
- `grille` — barème /20 : fonctionnel 40 %, qualité/tests 25 %, sécurité 10 %, architecture 15 %, documentation 10 %

Progression : projets 1–3 guidés (squelette et critères détaillés), 4–7 semi-guidés, 8–10 autonomes ;
le capstone est un produit complet choisi par l'apprenant dans une liste, présenté au jury.

Évaluation du parcours : livrables hebdomadaires 20 %, portfolio 40 %, capstone 40 %.

Hors périmètre du socle : corrigés de référence des 55 projets (sous-projet ultérieur si souhaité).

### 4.4 Cohorte pilote
- `LMS Batch` « Promo 1 — Fondamentaux Data Science », contenant le Parcours 0, dates paramétrables,
  évaluateur = rôle jury. Pas de prix (gratuit jusqu'au sous-projet 2).

### 4.5 Rôles
Rôles natifs LMS : `Course Creator` (formateur), `Batch Evaluator` (jury), `LMS Student` (apprenant).
Aucun rôle maison.

### 4.6 Docker
- Image unique construite depuis `frappe/bench` pinné sur un digest, `bench init --frappe-branch version-15`,
  `get-app payments --branch version-15`, `get-app lms --branch main` **pinné sur un commit/tag**,
  `openlab_academy` copié, `bench build` à la construction.
- Services : mariadb 11.4, redis, app (web + worker + scheduler + socketio).
- Secrets (mot de passe root DB, admin) via `.env` ; `.env*` gitignoré, `.env.example` versionné.
- Démarrage < 1 min après construction ; données dans des volumes nommés (`sites`, `mariadb`).

## 5. Flux

`docker-compose up` → entrypoint : si le site n'existe pas → `new-site` + `install-app payments lms openlab_academy`
→ `after_install` applique réglages + seed → `bench start`.

## 6. Erreurs

- Seed : transaction par parcours ; échec = rollback du parcours + log explicite, les autres parcours passent.
- YAML invalide : erreur de validation avec le chemin du champ fautif, avant toute écriture.
- Build Docker : version de LMS pinnée pour éviter la casse de `develop` constatée sur le POC.

## 7. Tests

- `tests/test_seed.py` (FrappeTestCase) : 5 cours créés ; nombre de chapitres/leçons/devoirs conforme
  au YAML ; chaque parcours a exactement 10 projets + 1 capstone, chaque fiche complète (tous champs requis,
  `apres_module` existant) ; seconde exécution = aucun doublon ; modification d'un module dans le YAML = mise à jour.
- Validation YAML : champ manquant → erreur explicite.
- Vérification de bout en bout réelle : compte apprenant → inscription à la cohorte → lecture d'une leçon
  → rendu d'un devoir → visible côté évaluateur.

## 8. Critères de succès

- Image construite, `docker-compose up` → plateforme habillée OpenLab en français sur `localhost:8000`.
- 5 parcours publiés, chaque module avec son devoir, 10 projets + 1 capstone par parcours, une cohorte pilote.
- Tests verts ; parcours apprenant de bout en bout vérifié manuellement.

## 9. Réglages paramétrables (ajout du 2026-10-16)

Décision utilisateur : tout paramètre métier est réglable sans développeur via un écran Frappe.

- DocType single **« Reglages OpenLab Academy »** (module OpenLab Academy), lecture/écriture réservées à System Manager,
  initialisé avec les valeurs actuelles (after_install + patch pour les sites existants). Champs :
  - Pédagogie : `projets_par_portfolio` (10), `heures_par_module` (8), `delai_ouverture_semaines` (2), `jour_ouverture` (Lundi).
  - Barème : table (critère, poids) — total = 100.
  - Exigences qualité communes : table (texte).
  - Rythmes : table (code, libellé, heures lundi…dimanche) — ≥ 1 rythme, codes uniques, total > 0.
  - Séances : `heure_debut` (18:30), `heure_fin` (20:30), `fuseau` (Africa/Abidjan).
  - Cohorte pilote : `parcours_pilote`, `formateur`.
  - Plateforme : `nom` (OpenLab Academy), `logo`, `langue` (fr), `devise` (XOF).
- Domaine : value object `Reglages` (défauts = valeurs actuelles) portant les invariants ; `Rythme` devient une donnée
  (plus une énumération). Le contrôleur du DocType valide en construisant `Reglages` : une incohérence est refusée.
- Surcharge par parcours : clé YAML facultative `parametres:` (`projets_par_portfolio`, `heures_par_module`,
  `delai_exercices_minutes`, `tentatives_max`, `score_min`) ; toute autre clé est refusée. Les trois réglages
  d'exercices valent, sans surcharge, ceux de la plateforme ; `delai_exercices_minutes` exige au moins 1 minute,
  car sur un parcours la valeur 0 signifie « appliquer le réglage global » (ajout du 2026-11-15).
- Port applicatif `SourceReglages.charger() -> Reglages` ; adaptateur Frappe. Un changement de réglages s'applique aux
  prochaines publications et cohortes, jamais rétroactivement.

## 10. Exercices de fin de leçon (ajout du 2026-10-16)

Décision utilisateur : après chaque module, un quiz obligatoire et une mise en situation.
- Réglages (écran) : `questions_par_quiz` = 5, `tentatives_max` = 3, `score_min` = **100 %**, `delai_exercices_minutes` = 60.
- Contenu (YAML du module) : `quiz` (exactement `questions_par_quiz` questions : énoncé, 2 à 6 options, ≥ 1 bonne
  réponse, explication) et `mise_en_situation` (texte). Générés pour les 4 parcours, à relire par les formateurs.
- Publication : un `LMS Quiz` par leçon (max_attempts, passing_percentage, réponses montrées) + un devoir
  « Mise en situation » ; la leçon affiche le conseil de relire le cours après 3 échecs ; LMS « quiz obligatoire » activé.
- Verrou d'1 h **côté serveur** : la première ouverture d'une leçon par un apprenant est enregistrée
  (surcharge de `lms.lms.utils.get_lesson`) ; toute réponse au quiz ou à la mise en situation avant
  `ouverture + délai` est refusée avec le temps restant. Formateurs et administrateurs ne sont pas bloqués.
- Réglages propres à un parcours (ajout du 2026-11-15) : `delai_exercices_minutes`, `tentatives_max` et `score_min`
  se règlent parcours par parcours sous `parametres:`. Le value object `ReglagesExercices` porte les invariants, et
  `Reglages.exercices` comme `Parcours.exercices` le livrent. Le quiz LMS et la phrase de la leçon prennent les
  valeurs du parcours ; le délai est en plus posé sur le parcours (champ personnalisé `delai_exercices_minutes` de
  `LMS Course`, niveau administrateur) pour que le verrou le lise à chaque soumission, avec repli sur le réglage
  global quand le champ vaut 0.
