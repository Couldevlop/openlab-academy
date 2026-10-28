# OpenLab Academy — Plateforme bilingue français / anglais

Date : 2026-10-28 · Dépôt : `Couldevlop/openlab-academy` (publié depuis le monorepo `D:\OPENLAB`, dossier
`Openlab_Academy/`) · Suite du paiement des parcours.

## 1. Intention

OpenLab Academy accueille aussi des apprenants, correcteurs et intendants anglophones. Toute personne doit pouvoir
utiliser la plateforme entière en français ou en anglais, à son choix, sans quitter la langue choisie d'un écran à
l'autre ni dans les e-mails qu'elle reçoit. Les contenus pédagogiques restent dans leur langue d'origine pour cette
première version.

## 2. Décisions de l'utilisateur

- **Pour tout le monde** : visiteurs, apprenants, correcteurs, intendants, administrateurs.
- **V1 = l'interface seulement** : libellés, boutons, messages, e-mails, écrans. **Les cours ne sont pas traduits**
  (titres, descriptions, leçons, quiz, grilles d'évaluation, YAML des parcours restent tels quels).
- **Au choix de la personne** : un sélecteur FR / EN visible partout (site public, LMS, `/espace`, bureau `/app`).
  Le choix est **retenu sur le compte** ; pour un visiteur non connecté, il est retenu par cookie.
- Ordre des chantiers : les écrans d'abord (fait), la traduction ensuite (ce document).

## 3. Choix faits par Claude (à contrôler)

- **Français par défaut** : langue système `fr`, langue d'un nouveau compte `fr`, visiteur sans choix ni cookie → `fr`
  (l'en-tête `Accept-Language` du navigateur n'est **pas** suivi : public d'abord ivoirien).
- **Chaque message sortant part dans la langue du destinataire** (e-mail, SMS, WhatsApp), pas dans celle de l'acteur
  qui le déclenche (ex. un intendant francophone renvoie un rendu à un apprenant anglophone → message en anglais).
- **`/espace` (Vue) : dictionnaire typé maison**, sans bibliothèque i18n : un objet `fr` de référence et un objet `en`
  du même type (clé manquante = erreur `vue-tsc`), une fonction `t(clé, paramètres)`. Raison : une soixantaine de
  libellés par écran au plus, pas de pluriels complexes, zéro dépendance, typage strict déjà en place (zod, vue-tsc).
- **Code Python : mécanisme standard Frappe** — chaînes source en français enveloppées dans `_()`, traductions dans
  `openlab_academy/translations/en.csv` (ou `locale/en.po`, selon ce que la version de Frappe du dépôt charge ; le
  builder vérifie). Le français étant la langue source, aucun fichier `fr` n'est nécessaire pour notre app.
- **LMS et Frappe** : les traductions françaises fautives ou absentes (« Maison » → « Accueil », « Enroll Now »,
  « Getting started » restés en anglais…) sont corrigées par surcharge dans les traductions de notre app, sans
  modifier les apps `lms` et `frappe`.

**Décision de l'utilisateur (2026-10-28)** : la correction couvre **tous les écrans apprenant et visiteur du LMS**
(catalogue, page cours, leçons, quiz, profil, inscription, connexion), relus intégralement. Les écrans formateur et
admin du LMS gardent la traduction Frappe telle quelle. L'anti-objectif « texte anglais visible par un francophone »
s'applique à ce périmètre.
- **Langue d'un compte** : `User.language` fait foi, sans indicateur supplémentaire. Les comptes existants gardent leur
  valeur (vide = `fr`). Le cookie du visiteur sert seulement à **initialiser la langue d'un compte créé** pendant sa
  visite ; il n'écrase jamais la langue d'un compte existant. Pas de champ personnalisé, pas de migration.
- **Destinataire d'un rappel** : la langue est celle de l'apprenant du dossier, même si le numéro ou l'adresse est celui
  d'un payeur. Pas de langue par contact.
- **WhatsApp sans modèle anglais** : rien n'est envoyé sur ce canal (statut `ignore` journalisé). L'e-mail et le SMS
  partent quand même en anglais. Aucun message n'est envoyé dans une autre langue que celle du destinataire.
- **Historique déjà enregistré** : les nouveaux messages stockés (journaux de copie `chaine.py`, notifications) sont
  enregistrés sous forme de code + paramètres et traduits à l'affichage ; l'historique existant reste en français
  (pas de migration des anciens enregistrements).
- **Page de paiement CinetPay** : incluse ; la langue transmise (`"lang"` dans `infrastructure/cinetpay.py`, aujourd'hui
  `"fr"` fixe) suit celle de l'apprenant.
- **Certificats LMS** (PDF) : exclus de la V1. Ce sont des documents qui reprennent le titre du cours, et leur gabarit
  appartient au LMS.
- **Nombres, montants, dates** : formatés selon la langue de la personne (`fr-FR` / `en-GB`) ; la devise reste
  XOF/FCFA dans les deux langues. Fuseau inchangé (Africa/Abidjan).

## 4. Périmètre

### Inclus
1. **Choix et mémorisation de la langue**
   - Compte connecté : champ standard `User.language` (`fr` ou `en`), modifiable depuis le sélecteur sans passer par
     le formulaire Utilisateur. Seules les valeurs `fr` et `en` sont acceptées (liste blanche côté serveur).
   - Visiteur : cookie `preferred_language` (mécanisme Frappe) ; à la connexion, si le compte n'a jamais choisi, le
     choix du visiteur est repris.
   - Le sélecteur recharge la page dans la nouvelle langue ; il est accessible au clavier et lisible par un lecteur
     d'écran (libellé « Langue / Language »).
2. **Site public et pages de connexion / inscription** (pages web Frappe et LMS) : traduits via `_()` et les fichiers
   de traduction.
3. **LMS (interface Vue frappe-ui de Frappe LMS)** : traduit par les fichiers de traduction ; corrections du français
   (§3) ; anglais natif du LMS conservé.
4. **`/espace` (nos écrans Vue)** : tous les libellés, messages d'erreur, statuts (`domaine/correction.ts` STATUTS,
   etc.), titres de page, textes d'aide, `aria-label`, formats de dates et nombres (`Intl` lit la langue courante au
   lieu de `fr-FR` codé en dur : `dates.ts`, `grille.ts`, `intendance.ts`, `paiement.ts`). La langue est fournie par
   le serveur dans les droits de session (`droits()`), pas devinée côté client.
5. **Messages serveur** : tous les `frappe.throw`, messages de validation des doctypes et textes renvoyés à l'interface
   (~40 `frappe.throw` aujourd'hui, plus les messages construits dans `application/` — ex. `retours.py` RENVOYEE).
   Le domaine (`domain/`) ne produit pas de phrase traduite : il renvoie un code et ses paramètres ; la traduction se
   fait dans `application/` ou `entrypoints/` (architecture hexagonale conservée).
6. **E-mails, SMS, WhatsApp** : gabarits `templates/emails/rappel_paiement.{html,txt}` et tout message de
   `application/` (rappels, retours, paiements) rendus dans la langue du destinataire. WhatsApp : le code langue du
   modèle Meta (`canaux.py`, aujourd'hui `"fr"` fixe) suit le destinataire ; si aucun modèle anglais n'est configuré,
   repli sur le modèle français (réglage dans l'écran de réglages de la plateforme).
7. **Bureau `/app`** : libellés de nos 29 doctypes (champs, sections, descriptions, options de Select), rapports,
   espaces de travail et messages de nos contrôleurs ; le reste du bureau est déjà traduit par Frappe.
8. **Exports** (Excel du journal de paiements, etc.) : en-têtes de colonnes dans la langue de la personne qui exporte.

### Exclu (V1)
- Contenu des cours : titres, descriptions, leçons, quiz, grilles et barèmes, YAML des parcours, livres et supports.
- Pré-correction IA : la langue des retours générés n'est pas pilotée par ce chantier.
- Toute autre langue que fr / en ; traduction automatique.
- URLs localisées (pas de `/en/...`) ; SEO multilingue (`hreflang`).

### Anti-objectifs (échec même si « ça marche »)
- Un écran ou un e-mail **mélangeant** les deux langues dans l'interface (hors contenu de cours).
- Un message envoyé à quelqu'un dans la langue d'un autre.
- Une clé de traduction brute (`ecran.titre`) ou un texte anglais du LMS visible par un francophone.
- Une régression du français actuel (formulations validées pendant les tests de bout en bout).
- Un choix de langue perdu au rechargement, à la déconnexion/reconnexion ou entre LMS et `/espace`.

## 5. Contraintes

- Frappe v15 + Frappe LMS, app `openlab_academy` ; front `/espace` Vue 3 + TypeScript (vitest, zod/mini, prettier,
  eslint, vue-tsc). Ne pas modifier les apps `frappe` ni `lms`.
- Couverture back ≥ 99 % (CI) ; tests front verts ; les tests back tiennent sur un site **neuf**.
- Tests à prévoir au minimum : chaque écran `/espace` rendu en `en` sans clé manquante ; parité des clés fr/en
  (vérifiée à la compilation + un test) ; un `frappe.throw` traduit selon la langue de l'utilisateur ; un rappel de
  paiement rendu en anglais pour un destinataire `en` déclenché par un acteur `fr` ; choix de langue refusé hors
  `fr`/`en` ; persistance compte et cookie.
- Sécurité : la langue est une donnée d'entrée — liste blanche stricte, jamais interpolée dans un chemin de fichier,
  une requête ou du HTML ; les paramètres insérés dans une phrase traduite restent échappés.
- Validation finale dans Chrome sur la pile de production locale (`ol-academy`), en FR puis en EN, avec chaque compte
  (apprenant, correcteur, intendant, responsable, administrateur), sur ordinateur et téléphone (375 px).
- Machine de développement à 8 Go : ne pas faire tourner la pile `ol-academy` et la suite de tests en même temps.

## 6. Laissé au builder

- Format exact des fichiers de traduction de l'app (CSV ou `.po`) selon la version de Frappe installée.
- Emplacement et apparence du sélecteur dans chaque zone (respect de la charte : Montserrat / Nunito Sans, couleurs).
- Découpage du dictionnaire `/espace` (un fichier par écran ou un fichier unique).
- Stratégie pour reprendre le choix du visiteur à la connexion.
- Ordre de livraison : proposition — 1) choix et mémorisation, 2) `/espace`, 3) messages serveur et e-mails,
   4) LMS et site public, 5) bureau `/app`.
