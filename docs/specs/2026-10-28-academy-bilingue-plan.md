# Plateforme bilingue FR / EN — plan de réalisation

> **Pour l'exécutant :** suivre ce plan tâche par tâche (superpowers:subagent-driven-development ou
> superpowers:executing-plans). Étapes en cases à cocher (`- [ ]`).

**But :** toute l'interface d'OpenLab Academy (site public, LMS côté apprenant, `/espace`, bureau `/app`, e-mails,
SMS, WhatsApp, page CinetPay, exports) en français ou en anglais au choix de la personne, sans traduire les cours.

**Architecture :** la langue est une donnée de session résolue par Frappe (`frappe.local.lang`) : `User.language` pour
un compte, cookie `preferred_language` pour un visiteur, `fr` sinon. Côté Python, chaînes source françaises dans `_()`
et traductions dans `openlab_academy/translations/en.csv` (anglais) et `translations/fr.csv` (surcharges du français
du LMS et de Frappe) — Frappe v15 charge ces CSV après les `.mo` de chaque app, et notre app, installée après `lms`,
l'emporte. Le domaine ne traduit rien ; `application/` reçoit une fonction de traduction par port. Côté `/espace`, un
dictionnaire typé maison (`fr` de référence, `en` du même type) et une fonction `t()`, langue fournie par
`droits()`. Un sélecteur FR/EN (script commun injecté dans le LMS, le site et le bureau ; composant Vue dans
`/espace`) appelle une méthode whitelistée puis recharge la page.

**Pile :** Frappe v15 + LMS, Python 3.11 ; Vue 3 + TypeScript strict, zod/mini, Vitest.

**Spec :** `docs/specs/2026-10-28-academy-bilingue-design.md`

## Contraintes globales

- Langues acceptées : **`fr` et `en` uniquement** (liste blanche, `domain/langues.py`) ; défaut **`fr`** ; l'en-tête
  `Accept-Language` n'est **jamais** suivi.
- Formats : `fr` → `fr-FR`, `en` → `en-GB` ; devise XOF/FCFA dans les deux langues ; fuseau Africa/Abidjan inchangé.
- Contenus de cours jamais traduits (titres, leçons, quiz, grilles, YAML) ; certificats PDF du LMS exclus.
- Aucun message sortant dans une autre langue que celle du destinataire (langue de l'apprenant du dossier) ;
  WhatsApp sans modèle anglais configuré → statut `ignore`.
- Ne modifier ni `apps/frappe` ni `apps/lms` : surcharges par hooks, `override_whitelisted_methods`, CSV de traduction.
- Le français actuel est la référence : aucune formulation française existante ne change, sauf corrections du LMS.
- Paramètres insérés dans une phrase traduite : échappés en HTML (e-mails, pages) ; la langue n'est jamais interpolée
  dans un chemin, une requête ou du HTML.
- Tests : TDD ; couverture back ≥ 99 % (`bash docker/dev-test.sh [module]`), front (`npm test`, `npm run typecheck`,
  `npm run lint` dans `apps/openlab_academy/frontend`) ; tests Frappe verts **sur un site neuf** (CI).
- Mémoire 8 Go : arrêter la pile `ol-academy` pendant les tests du banc de dev, et inversement.
- Aucune trace d'outillage dans le code, les commits ou les fichiers ; commits conventionnels en français.

## Points de vigilance (à épingler par un test)

1. **Visiteur avec un navigateur anglais et sans cookie** : la page s'affiche en français (Tâche 1).
2. **Valeur de langue hostile** (`de`, `""`, `../en`, `en<script>`) : refusée, rien n'est écrit sur le compte ni en
   cookie (Tâche 1).
3. **Rappels en lot** : un rappel `en` puis un rappel `fr` dans la même tâche planifiée → chacun dans sa langue, et
   `frappe.local.lang` restauré après chaque envoi (Tâche 5).
4. **Changement de langue dans le LMS puis ouverture de `/espace`** : même langue, lue sur le compte (Tâches 1 et 7).
5. **Nom d'apprenant contenant du HTML** (`<b>Ama</b>`) dans un e-mail anglais : échappé (Tâche 5).

---

### Tâche 1 : choix et mémorisation de la langue

**Fichiers :**
- Créer : `openlab_academy/domain/langues.py`, `openlab_academy/entrypoints/langue.py`
- Modifier : `openlab_academy/entrypoints/http.py` (`before_request`), `openlab_academy/hooks.py`
  (`override_whitelisted_methods`, `doc_events` User)
- Test : `openlab_academy/tests/test_langues.py`, `openlab_academy/tests/test_langue_frappe.py`

**Interfaces :**
- Produit :
  - `LANGUES: tuple[str, ...] = ("fr", "en")`, `DEFAUT = "fr"`, `normaliser(valeur: object) -> str | None`
    (renvoie la langue si elle est exactement dans `LANGUES`, sinon `None`), `locale(langue: str) -> str`
    (`"fr-FR"` / `"en-GB"`).
  - `@frappe.whitelist(allow_guest=True, methods=["POST"]) choisir(langue: str) -> str` : compte connecté →
    `User.language` (sans passer par les permissions du formulaire User, seul ce champ) ; visiteur → cookie
    `preferred_language` (1 an, `SameSite=Lax`, `HttpOnly` inutile car Frappe le lit côté serveur seulement) ;
    valeur refusée → `frappe.throw(_("Langue non prise en charge."), frappe.ValidationError)`.
  - `get_translations()` (surcharge de `lms.lms.api.get_translations`) : `get_all_translations(frappe.local.lang)`.
  - `initialiser_langue(user, method)` (`doc_events["User"]["after_insert"]`) : si le cookie du visiteur est une
    langue valide et différente de `fr`, l'écrit sur le nouveau compte ; n'agit jamais sur un compte existant.

- [ ] **Step 1 : tests du domaine** — `test_langues.py` : `normaliser("en") == "en"`, `normaliser("EN") is None`,
  `normaliser("de") is None`, `normaliser("") is None`, `normaliser(None) is None`, `normaliser("../en") is None`,
  `locale("en") == "en-GB"`, `locale("fr") == "fr-FR"`.
- [ ] **Step 2 : lancer** `bash docker/dev-test.sh openlab_academy.tests.test_langues` → FAIL (module absent).
- [ ] **Step 3 : écrire `domain/langues.py`.**
- [ ] **Step 4 : tests Frappe** — `test_langue_frappe.py` :
  - `test_choisir_ecrit_la_langue_du_compte` : connecté `Administrator`, `choisir("en")` → `User.language == "en"`.
  - `test_choisir_refuse_une_langue_hors_liste` : pour `de`, `""`, `../en`, `en<script>` → `ValidationError`, langue
    du compte inchangée, aucun cookie posé.
  - `test_visiteur_cookie_pose` : `frappe.set_user("Guest")`, `choisir("en")` → `frappe.local.cookie_manager` contient
    `preferred_language=en`.
  - `test_visiteur_accept_language_ignore` : requête Guest avec `Accept-Language: en-US` et sans cookie →
    `frappe.local.lang == "fr"` après `before_request`.
  - `test_visiteur_cookie_suivi` : Guest + cookie `en` → `frappe.local.lang == "en"`.
  - `test_traductions_lms_suivent_le_visiteur` : Guest + cookie `en`, `get_translations()` est le dictionnaire `en`
    (une clé connue de `en.csv` présente).
  - `test_nouveau_compte_reprend_le_cookie` / `test_compte_existant_inchange`.
  - `test_methode_publique_post_seulement` : `choisir` est whitelistée `allow_guest`, méthodes `["POST"]`.
- [ ] **Step 5 : lancer** → FAIL.
- [ ] **Step 6 : écrire `entrypoints/langue.py`, compléter `before_request`** (Guest sans `_lang` ni cookie valide →
  `frappe.local.lang = DEFAUT` ; vérifier dans `frappe/app.py` que le hook passe bien après la résolution de la
  langue), déclarer les hooks.
- [ ] **Step 7 : lancer les deux modules** → PASS.
- [ ] **Step 8 : commit** `feat(academy): choix de la langue FR/EN retenu sur le compte ou par cookie`.

### Tâche 2 : fichiers de traduction et garde-fou de complétude

**Fichiers :**
- Créer : `openlab_academy/translations/en.csv`, `openlab_academy/translations/fr.csv`,
  `openlab_academy/tests/test_traductions.py`

**Interfaces :**
- Produit : format CSV Frappe (`source,traduction,contexte`) ; `en.csv` = toutes nos chaînes source françaises ;
  `fr.csv` = surcharges du français de `lms`/`frappe` (source anglaise du LMS → français OpenLab).

- [ ] **Step 1 : test** `test_toute_chaine_traduisible_a_son_anglais` : extrait par regex chaque littéral de `_("…")`
  dans `openlab_academy/**/*.py` (hors `tests/`) et `{{ _("…") }}` dans `templates/**/*.html|txt` ; chacun doit être une
  clé de `en.csv` avec une traduction non vide. `test_csv_bien_formes` : trois colonnes au plus, pas de doublon de clé.
  `test_surcharges_lms_appliquees` : `frappe.translate.get_all_translations("fr")["Home"] == "Accueil"`.
- [ ] **Step 2 : lancer** → FAIL (fichiers absents).
- [ ] **Step 3 : créer les deux CSV** (`fr.csv` démarre avec « Home → Accueil », « Enroll Now → S'inscrire »,
  « Getting started → Bien démarrer » ; vider le cache de traduction dans le test).
- [ ] **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): fichiers de traduction de l'app et contrôle de complétude`.

### Tâche 3 : sélecteur de langue hors `/espace`

**Fichiers :**
- Créer : `openlab_academy/public/js/langue.js`
- Modifier : `openlab_academy/infrastructure/habillage.py` (injection dans le LMS), `openlab_academy/hooks.py`
  (`web_include_js`, `app_include_js`), `openlab_academy/public/css/openlab.css`
- Test : `openlab_academy/tests/test_habillage.py`

**Interfaces :**
- Consomme : `openlab_academy.entrypoints.langue.choisir` (Tâche 1).
- Produit : bouton `button.ol-langue` (texte « EN » quand la page est en français, « FR » sinon, `aria-label`
  « Langue / Language », `lang` de `<html>` pour savoir la langue courante) ; au clic, POST `choisir` avec le jeton CSRF
  de la page (`frappe.csrf_token` ou `window.csrf_token`) puis `location.reload()`. Placement : en-tête du LMS (barre
  latérale), barre du site public, barre du bureau (à côté de l'avatar) ; style de la charte.

- [ ] **Step 1 : tests** : `injecter()` ajoute `/assets/openlab_academy/js/langue.js` une seule fois ; `hooks.web_include_js`
  et `hooks.app_include_js` le contiennent ; le script n'interpole aucune donnée de page dans du HTML (`innerHTML`
  absent du fichier).
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : écrire `langue.js`, l'injecter, le styler.**
- [ ] **Step 4 : lancer** → PASS ; vérifier le bouton dans Chrome sur `/lms`, `/` et `/app` (pile `ol-academy`).
- [ ] **Step 5 : commit** `feat(academy): sélecteur FR/EN dans le LMS, le site et le bureau`.

### Tâche 4 : messages serveur traduits

**Fichiers :**
- Modifier : tous les `frappe.throw` et textes renvoyés à l'interface dans `entrypoints/` et `application/`
  (dont `application/retours.py` `RENVOYEE`, `entrypoints/evaluation_api.py`, `entrypoints/paiement_api.py`),
  les `validate()` des contrôleurs de `openlab_academy/openlab_academy/doctype/`, `translations/en.csv`
- Test : `openlab_academy/tests/test_messages_traduits.py`

**Interfaces :**
- Produit : `Traduire = Callable[[str], str]` dans `application/ports_langue.py`, injecté là où `application/` compose une
  phrase (défaut : identité, pour les tests purs) ; les entrypoints passent `frappe._`. Les phrases à trous utilisent
  des paramètres nommés : `_("Votre rendu vous est renvoyé : {motifs}. …").format(motifs=…)`.
- Le domaine renvoie des exceptions et codes inchangés ; seuls `application/` et `entrypoints/` traduisent.

- [ ] **Step 1 : tests** : utilisateur de test en `en`, `evaluation_api` sans connexion → message
  `"Login required."` ; renvoi d'un rendu → texte anglais de `RENVOYEE` avec les motifs ; même scénario en `fr` →
  texte français actuel, à l'identique.
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : envelopper les chaînes, compléter `en.csv`** (le test de la Tâche 2 signale toute clé manquante).
- [ ] **Step 4 : lancer le module, puis toute la suite** (`bash docker/dev-test.sh`) → PASS, couverture ≥ 99 %.
- [ ] **Step 5 : commit** `feat(academy): messages du serveur en français ou en anglais`.

### Tâche 5 : rappels, e-mails, SMS, WhatsApp et CinetPay dans la langue du destinataire

**Fichiers :**
- Modifier : `application/rappels.py` (`Destinataire.langue: str = "fr"`, composition du `Message` par `Traduire`),
  `infrastructure/rappels_frappe.py` (langue = `User.language` de l'apprenant du dossier, défaut `fr`),
  `infrastructure/canaux.py` (rendu sous la langue du destinataire ; WhatsApp `language.code` = langue, modèle anglais
  lu dans les réglages, absent → `DestinataireInjoignable`), `infrastructure/cinetpay.py` (`"lang"` = langue de
  l'apprenant), `templates/emails/rappel_paiement.{html,txt}` (textes dans `_()`), doctype des réglages de la
  plateforme (champ `whatsapp_modele_en`, Data, facultatif), `translations/en.csv`
- Test : `tests/test_rappels.py`, `tests/test_canaux.py`, `tests/test_cinetpay.py` (existants, compléter)

**Interfaces :**
- Produit : `en_langue(langue: str)` — gestionnaire de contexte dans `infrastructure/canaux.py` qui pose
  `frappe.local.lang` et le restaure à la sortie, même en cas d'exception.

- [ ] **Step 1 : tests** : rappel pour un apprenant `en` déclenché par un acteur `fr` → sujet et texte anglais, e-mail
  rendu en anglais ; lot `en` puis `fr` → chacun dans sa langue et `frappe.local.lang` identique avant/après ;
  WhatsApp `en` sans modèle anglais → statut `ignore`, e-mail et SMS envoyés ; avec modèle → `language.code == "en"` ;
  nom `<b>Ama</b>` échappé dans l'e-mail ; paiement CinetPay d'un apprenant `en` → `"lang": "en"`.
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer les trois modules** → PASS.
- [ ] **Step 5 : commit** `feat(academy): rappels et paiement dans la langue de l'apprenant`.

### Tâche 6 : historique et journaux traduits à l'affichage

**Fichiers :**
- Modifier : les points d'affichage du journal (`Journal Note OpenLab`, journal de paiement) — API qui renvoie
  l'historique à `/espace` (`entrypoints/evaluation_api.py`, `entrypoints/paiement_api.py`) et formulaire du bureau ;
  `translations/en.csv`
- Test : `tests/test_journal_traduit.py`

**Interfaces :**
- Décision : l'action déjà stockée (« pairs sautés », « jury sauté », « étape suivante », « rappel de relecture »,
  « relecture réattribuée », …) **est** le code ; elle reste stockée telle quelle et est traduite à la lecture par
  `_()` (clé = chaîne française). Les paramètres (dict JSON) restent des valeurs, jamais des phrases. Aucune migration.
  Toute nouvelle action journalisée doit avoir son entrée dans `en.csv` (test de la Tâche 2 étendu à la liste
  `ACTIONS` exportée par `application/chaine.py`).

- [ ] **Step 1 : tests** : historique lu par un utilisateur `en` → `"peers skipped"` ; par un `fr` → `"pairs sautés"` ;
  chaque élément de `ACTIONS` a sa traduction.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : implémenter.** **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): historique des copies et des paiements traduit à l'affichage`.

### Tâche 7 : `/espace` — socle i18n et sélecteur

**Fichiers :**
- Créer : `frontend/src/i18n/fr.ts`, `frontend/src/i18n/en.ts`, `frontend/src/i18n/index.ts`,
  `frontend/src/i18n/index.test.ts`, `frontend/src/interface/composants/ChoixLangue.vue` (+ test)
- Modifier : `openlab_academy/www/espace.py` (`droits()` renvoie `langue`), `frontend/src/application/ports.ts`
  (`Droits.langue: Langue`), `frontend/src/infrastructure/navigateur/session.ts` (zod : `langue` optionnel, défaut
  `'fr'`, valeur hors liste → `'fr'`), `frontend/src/domaine/{dates,grille,intendance,paiement}.ts` (le format reçoit
  la locale au lieu de `'fr-FR'` codé en dur), `frontend/src/interface/composants/EnTete.vue`, `frontend/src/main.ts`
- Test : `tests/test_espace.py` (attentes de `droits()` complétées par `"langue"`)

**Interfaces :**
- Produit :
  - `type Langue = 'fr' | 'en'` ; `const fr = { … } as const` ; `type Dictionnaire = DeepString<typeof fr>` ;
    `const en: Dictionnaire` (clé manquante ou en trop = erreur `vue-tsc`).
  - `t(cle: CheminDe<Dictionnaire>, parametres?: Record<string, string | number>): string` — remplace `{nom}` ;
    `localeDe(langue: Langue): 'fr-FR' | 'en-GB'` ; fournis aux écrans par `provide`/`inject` (`CLE_I18N`).
  - `ChoixLangue.vue` : même comportement que le bouton de la Tâche 3 (POST `choisir`, rechargement).

- [ ] **Step 1 : tests** : `t('commun.monEspace')` en `fr` → « Mon espace », en `en` → « My space » ; paramètre
  remplacé ; `session` avec `langue: 'de'` → `'fr'` ; `dates.ts` formate en `en-GB` quand on lui passe `'en-GB'` ;
  `droits()` Python renvoie `"langue": "en"` pour un compte `en` ; `ChoixLangue` appelle `choisir` avec `en`.
- [ ] **Step 2 : lancer** `npm test` et `bash docker/dev-test.sh openlab_academy.tests.test_espace` → FAIL.
- [ ] **Step 3 : implémenter** (les écrans existants appellent `t()` pour l'en-tête seulement à ce stade).
- [ ] **Step 4 : lancer** `npm test && npm run typecheck && npm run lint` et le module Python → PASS.
- [ ] **Step 5 : commit** `feat(academy): socle de traduction de l'espace et choix de la langue`.

### Tâche 8 : `/espace` — écrans paiement et administration

**Fichiers :** `frontend/src/interface/ecrans/{Accueil,Paiement,Intendance,Finances,Pilotage}.vue`,
`frontend/src/interface/composants/{FichePaiement,Indicateur,NavAgents,Puce,PuceStatut}.vue`,
`frontend/src/domaine/{paiement,intendance,pilotage}.ts` (libellés), `frontend/src/application/erreurs.ts`,
`frontend/src/i18n/{fr,en}.ts` ; tests existants de ces écrans.

- [ ] **Step 1 : tests** : pour chaque écran, un rendu en `en` ne contient aucun texte du dictionnaire `fr` ni aucune
  clé brute (motif `/\b[a-z]+\.[a-zA-Z.]+\b/`) ; les tests `fr` existants restent inchangés et verts.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : remplacer chaque libellé, `aria-label`, titre et message par `t()`.**
- [ ] **Step 4 : lancer** `npm test && npm run typecheck && npm run lint` → PASS.
- [ ] **Step 5 : commit** `feat(academy): écrans de paiement et d'administration en anglais`.

### Tâche 9 : `/espace` — écrans d'évaluation

**Fichiers :** `frontend/src/interface/ecrans/{Correcteur,Lots,Relecture,Retour}.vue`,
`frontend/src/interface/composants/{CopieRendue,GrilleCorrecteur,OngletsCorrection}.vue`,
`frontend/src/domaine/{correction,grille,lots,relecture,retour,versions,citation}.ts` (dont `STATUTS`),
`frontend/src/i18n/{fr,en}.ts` ; tests existants.

- [ ] **Step 1 : tests** : mêmes assertions que la Tâche 8 ; `STATUTS` en `en` (`renvoyee` → « returned to the
  learner », etc.) ; le **contenu** d'une grille et d'une copie (critères, texte de l'apprenant) n'est pas traduit.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : implémenter.** **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): écrans d'évaluation en anglais`.

### Tâche 10 : bureau `/app` et exports

**Fichiers :**
- Modifier : `translations/en.csv` (libellés, sections, descriptions, options de Select de nos 29 doctypes, espaces de
  travail, rapports), en-têtes de l'export Excel du journal de paiements (`infrastructure/tableaux_paiement_frappe.py`
  ou son entrypoint) via `_()`
- Test : `tests/test_traductions.py` (étendu), `tests/test_tableaux_paiement*.py`

- [ ] **Step 1 : tests** : chaque `label`, `description` et option de `Select` des JSON de
  `openlab_academy/openlab_academy/doctype/*/*.json` et des espaces de travail a une entrée dans `en.csv` ; export
  demandé par un utilisateur `en` → en-têtes anglais, par un `fr` → en-têtes actuels.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : compléter.** **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): bureau et exports en anglais`.

### Tâche 11 : LMS côté apprenant et site public en français correct

**Fichiers :** `translations/fr.csv`, `translations/en.csv` (pages web de notre app : connexion, inscription si
surchargées) ; test `tests/test_traductions.py`.

- [ ] **Step 1 : relevé** — dans Chrome, pile `ol-academy`, compte apprenant puis visiteur, en `fr` : catalogue, page
  cours, leçon, quiz, profil, inscription, connexion, paiement. Noter chaque texte anglais ou mal traduit (source
  anglaise exacte, lue dans `apps/lms/frontend/src` ou `apps/lms/lms/locale/fr.po`).
- [ ] **Step 2 : test** : chaque source relevée a sa traduction attendue dans `get_all_translations("fr")`.
- [ ] **Step 3 : lancer** → FAIL. **Step 4 : compléter `fr.csv`.** **Step 5 : lancer** → PASS.
- [ ] **Step 6 : commit** `fix(academy): français du LMS côté apprenant et visiteur`.

### Tâche 12 : validation de bout en bout

- [ ] **Step 1 :** reconstruire et relancer la pile `ol-academy` (`docker-compose -p ol-academy build` puis `up -d`,
  `bench --site academy.localhost migrate`), banc de dev arrêté.
- [ ] **Step 2 :** dans Chrome, pour chaque compte (visiteur, apprenant, correcteur, intendant, responsable,
  administrateur), en `fr` puis en `en`, sur ordinateur et à 375 px : parcourir chaque écran, vérifier l'absence de
  mélange de langues et de clé brute, la persistance du choix (rechargement, déconnexion/reconnexion, passage LMS →
  `/espace` → `/app`).
- [ ] **Step 3 :** déclencher un rappel de paiement et un renvoi de rendu pour un apprenant `en` depuis un intendant
  `fr` ; contrôler le contenu dans la file d'e-mails (Email Queue).
- [ ] **Step 4 :** corriger tout écart par une tâche courte (test d'abord), puis publier sur `develop` (subtree
  split) et vérifier la CI.
