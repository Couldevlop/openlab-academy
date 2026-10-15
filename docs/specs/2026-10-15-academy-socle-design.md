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

### 4.3 Cohorte pilote
- `LMS Batch` « Promo 1 — Fondamentaux Data Science », contenant le Parcours 0, dates paramétrables,
  évaluateur = rôle jury. Pas de prix (gratuit jusqu'au sous-projet 2).

### 4.4 Rôles
Rôles natifs LMS : `Course Creator` (formateur), `Batch Evaluator` (jury), `LMS Student` (apprenant).
Aucun rôle maison.

### 4.5 Docker
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
  au YAML ; seconde exécution = aucun doublon ; modification d'un module dans le YAML = mise à jour.
- Validation YAML : champ manquant → erreur explicite.
- Vérification de bout en bout réelle : compte apprenant → inscription à la cohorte → lecture d'une leçon
  → rendu d'un devoir → visible côté évaluateur.

## 8. Critères de succès

- Image construite, `docker-compose up` → plateforme habillée OpenLab en français sur `localhost:8000`.
- 5 parcours publiés, chaque module avec son devoir, une cohorte pilote.
- Tests verts ; parcours apprenant de bout en bout vérifié manuellement.
