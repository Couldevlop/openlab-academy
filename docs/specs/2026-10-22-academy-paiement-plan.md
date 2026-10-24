# Paiement des parcours — plan de réalisation

**But :** rendre les parcours payants (frais d'inscription + trois modes, échéances le 10 du mois, rappels J-7/J-3/J-1
sur trois canaux, blocage par parcours, CinetPay et virements, vue intendant et résumé administrateur).

**Architecture :** domaine pur (échéancier, statut, rappels) sans Frappe ; cas d'usage derrière des ports (dépôt de
dossiers, passerelle de paiement, canaux, journal) ; adaptateurs Frappe, CinetPay, SMS, WhatsApp ; points d'entrée
(hooks, API whitelistée, tâche planifiée). Écrans dans l'application Vue `/espace` existante. Le blocage n'est pas un
état stocké : il est **calculé à chaque requête** depuis l'échéancier, les paiements confirmés et le délai accordé
(aucune tâche ne peut bloquer à tort).

**Pile :** Frappe v15 + LMS, Python 3.11, `requests` ; Vue 3 + frappe-ui + TypeScript strict, Vitest.

**Spec :** `docs/specs/2026-10-22-academy-paiement-design.md`

## Contraintes globales

- Montants en **XOF entiers, multiples de 5** (contrainte CinetPay) : la console refuse un prix ou des frais non
  multiples de 5 ; les parts calculées sont des multiples de 5, le reste sur la dernière.
- Échéances **le 10 du mois** (`jour_echeance = 10`, réglable) ; dues « au plus tard le 10 » : en retard à partir du 11
  à 00:00, fuseau Abidjan (UTC).
- Rappels **7, 3 et 1 jours** avant (`delais_rappel = "7,3,1"`, réglable) ; canaux e-mail, SMS, WhatsApp, chacun
  ignoré s'il n'est pas configuré.
- Inscription refusée plus de **2 mois** après le début de la cohorte (`inscription_tardive_mois = 2`).
- Prix figés dans le dossier à l'inscription.
- Rôles jamais bloqués : `System Manager`, `Moderator`, `Course Creator`, `Batch Evaluator`, `Intendant OpenLab`
  (reprendre `ROLES_NON_BLOQUES` de `entrypoints/lms.py`, étendu).
- Secrets (clé API et clé secrète CinetPay, jetons SMS et WhatsApp) en champs `Password`, jamais renvoyés par l'API ni
  écrits dans un message d'erreur ou un journal.
- Tests : TDD ; couverture back ≥ 99 % (`bash docker/dev-test.sh`), front seuils existants (`npm test -- --coverage`) ;
  les tests Frappe passent **sur un site neuf** (CI).
- Aucune trace d'outillage dans le code, les commits ou les fichiers ; commits conventionnels en français.

## Points de vigilance (non couverts par la spec, à épingler par un test)

1. **Notification CinetPay rejouée ou falsifiée** : la même transaction reçue deux fois n'enregistre qu'un paiement ;
   un statut non confirmé par `/v2/payment/check` ou un `x-token` invalide n'enregistre rien (Tâche 5).
2. **Montant reçu différent du montant attendu** (paiement partiel côté opérateur) : enregistré pour le montant
   réellement confirmé, jamais pour le montant demandé (Tâche 5).
3. **Changement de mode alors que tout est déjà payé ou trop payé** (passage de mensuel à « une fois » après plusieurs
   mensualités) : reste dû ≥ 0, aucune échéance négative, dossier soldé (Tâche 1).
4. **Cohorte qui se termine le mois de l'inscription** (inscription tardive sur un parcours court) : au moins une
   échéance, le 10 du mois suivant (Tâche 1).
5. **Apprenant bloqué qui ouvre une leçon par l'API sans passer par une page** : `get_lesson` refuse aussi (Tâche 7).

---

### Tâche 1 : domaine — échéancier et changement de mode

**Fichiers :**
- Créer : `openlab_academy/domain/echeancier.py`
- Test : `openlab_academy/tests/test_echeancier.py`

**Interfaces :**
- Produit :
  - `class Mode(StrEnum): UNE_FOIS = "une_fois"; DEUX_TRANCHES = "deux_tranches"; MENSUEL = "mensuel"`
  - `@dataclass(frozen=True) class Tarif: frais_inscription: int; une_fois: int; deux_tranches: int; mensuel: int`
    avec `prix(mode: Mode) -> int` et `valider() -> None` (lève `TarifInvalide(ValueError)` : montant ≤ 0, non
    multiple de 5, frais ≥ un prix, ordre une_fois < deux_tranches < mensuel non respecté)
  - `@dataclass(frozen=True) class Echeance: date_limite: date; montant: int; libelle: str`
  - `echeancier(mode: Mode, tarif: Tarif, inscription: date, debut: date, fin: date, jour: int = 10) -> tuple[Echeance, ...]`
    — première ligne « Frais d'inscription » à la date d'inscription, puis le reste selon la spec
  - `replanifier(mode: Mode, tarif: Tarif, deja_paye: int, aujourd_hui: date, debut: date, fin: date, jour: int = 10) -> tuple[Echeance, ...]`
    — une ligne « Déjà versé » datée d'aujourd'hui pour `min(deja_paye, prix)` puis le reste `prix − déjà versé`
    réparti sur les dates du mode strictement postérieures à aujourd'hui
  - `inscription_permise(debut: date, aujourd_hui: date, mois: int = 2) -> bool`
  - `dixieme_suivant(d: date, jour: int = 10) -> date` (le `jour` du mois suivant `d`)

- [ ] **Étape 1 : tests rouges** — cas, avec `t = Tarif(50_000, 600_000, 700_000, 800_000)`, cohorte du 2026-11-02 au
  2027-02-01 :
  - `test_une_fois` : inscription 2026-10-15 → `[(2026-10-15, 50_000), (2026-11-10, 550_000)]`
  - `test_deux_tranches` : → `[(2026-10-15, 50_000), (2026-11-10, 325_000), (2026-12-10, 325_000)]` (mi-parcours
    2026-12-17 → 10 décembre)
  - `test_deux_tranches_mi_parcours_deja_passe` : inscription 2026-12-20 → seconde tranche le 10 du mois qui suit la
    première (2027-02-10)
  - `test_mensuel_parts_multiples_de_5` : `Tarif(50_000, 600_000, 700_000, 800_005)` → mensualités 2026-11-10,
    2026-12-10, 2027-01-10, 2027-02-10 ; chaque montant % 5 == 0 ; somme == 800_005 ; reste sur la dernière
  - `test_mensuel_cohorte_finie_le_mois_de_l_inscription` : au moins une mensualité, le 10 du mois suivant
  - `test_inscription_le_10_paie_le_10_du_mois_suivant` : inscription 2026-10-10 → reste au 2026-11-10
  - `test_replanifier_mensuel_vers_une_fois` : déjà payé 50_000 + 2 × 187_500 → une ligne « Déjà versé » 425_000 et
    175_000 à la prochaine date
  - `test_replanifier_deja_solde` : déjà payé ≥ prix → seule la ligne « Déjà versé » (= prix), aucune ligne négative
  - `test_inscription_permise` : début 2026-11-02 → vrai le 2027-01-02, faux le 2027-01-03
  - `test_tarif_invalide` : non multiple de 5, ordre faux, frais ≥ une_fois, montant nul → `TarifInvalide`
- [ ] **Étape 2 :** `cd D:\OPENLAB\Openlab_Academy\apps\openlab_academy && python -m pytest -q openlab_academy/tests/test_echeancier.py` → échec (module absent)
- [ ] **Étape 3 :** implémenter `domain/echeancier.py` (aucun import Frappe). Mi-parcours = `debut + (fin − debut) / 2` ;
  mois de mensualités = du mois suivant l'inscription au mois de `fin` inclus, au moins un ; parts =
  `(reste // n) // 5 * 5`, dernière = reste − somme des autres.
- [ ] **Étape 4 :** même commande → PASS
- [ ] **Étape 5 :** commit `feat(academy): échéancier de paiement (frais, trois modes, le 10 du mois, changement de mode)`

### Tâche 2 : domaine — statut d'un dossier et rappels dus

**Fichiers :**
- Créer : `openlab_academy/domain/dossier_paiement.py`
- Test : `openlab_academy/tests/test_dossier_paiement.py`

**Interfaces :**
- Consomme : `Echeance` (Tâche 1)
- Produit :
  - `class Statut(StrEnum): DISPENSE, SOLDE, A_JOUR, EN_RETARD` (valeurs `dispense`, `solde`, `a_jour`, `en_retard`)
  - `@dataclass(frozen=True) class Dossier: echeances: tuple[Echeance, ...]; paye: int; delai_jusqu_au: date | None = None; dispense: bool = False`
    avec `total` (somme des échéances), `reste` (`max(total − paye, 0)`), `du_echu(aujourd_hui) -> int` (somme des
    échéances dont `date_limite < aujourd_hui`), `prochaine(aujourd_hui) -> Echeance | None` (première échéance non
    couverte par le cumul payé)
  - `statut(dossier: Dossier, aujourd_hui: date) -> Statut` — `EN_RETARD` si `du_echu > paye` et pas de délai
    couvrant aujourd'hui (`aujourd_hui <= delai_jusqu_au`)
  - `bloque(dossier, aujourd_hui) -> bool` (≡ `statut == EN_RETARD`)
  - `@dataclass(frozen=True) class RappelDu: echeance: Echeance; jours_avant: int; montant: int`
  - `rappels_dus(dossier: Dossier, aujourd_hui: date, delais: tuple[int, ...] = (7, 3, 1)) -> tuple[RappelDu, ...]`
    — pour chaque échéance non couverte, si `date_limite − aujourd_hui` ∈ `delais` ; `montant` = part non couverte
- [ ] **Étape 1 : tests rouges** — `test_frais_non_payes_bloquent_le_jour_meme_suivant` (échéance d'inscription au
  2026-10-15 non payée → à jour le 15, en retard le 16) ; `test_echeance_du_10_en_retard_le_11` ;
  `test_paiement_partiel_reste_en_retard` ; `test_delai_couvre_jusqu_a_sa_date_incluse` ; `test_dispense_jamais_bloque` ;
  `test_solde` ; `test_rappels_7_3_1` (aucun rappel à J-2, montant = part non couverte) ;
  `test_pas_de_rappel_pour_une_echeance_couverte`.
- [ ] **Étape 2 :** pytest du fichier → échec
- [ ] **Étape 3 :** implémenter (cumul : les paiements couvrent les échéances dans l'ordre des dates)
- [ ] **Étape 4 :** PASS
- [ ] **Étape 5 :** commit `feat(academy): statut d'un dossier de paiement (retard, délai, dispense) et rappels dus`

### Tâche 3 : données — DocTypes, rôle Intendant, réglages et tarifs

**Fichiers :**
- Créer (DocTypes, `openlab_academy/openlab_academy/doctype/<nom>/`, JSON + `.py` minimal) :
  - `tarif_parcours_openlab` — `cours` (Link LMS Course, unique), `frais_inscription`, `prix_une_fois`,
    `prix_deux_tranches`, `prix_mensuel` (Int) ; `validate` → `Tarif(...).valider()` ; permissions écriture
    `System Manager`, `Intendant OpenLab`
  - `reglages_paiement_openlab` (Single) — section CinetPay : `cinetpay_site_id` (Data), `cinetpay_api_key`,
    `cinetpay_secret` (Password), `cinetpay_url_notification_base` (Data, URL publique du site) ; section SMS :
    `sms_url_jeton`, `sms_client_id` (Data), `sms_client_secret` (Password), `sms_expediteur` (Data) ; section
    WhatsApp : `whatsapp_phone_id` (Data), `whatsapp_jeton` (Password), `whatsapp_modele` (Data, nom du modèle
    approuvé) ; section échéances : `jour_echeance` (Int, 10), `delais_rappel` (Data, `7,3,1`),
    `inscription_tardive_mois` (Int, 2)
  - `dossier_paiement_openlab` — `apprenant` (Link User), `cours` (Link LMS Course), `cohorte` (Link LMS Batch),
    `mode` (Select : `une_fois`, `deux_tranches`, `mensuel`), `telephone` (Data, format E.164), `frais_inscription`,
    `prix_une_fois`, `prix_deux_tranches`, `prix_mensuel` (Int, figés), `dispense` (Check), `delai_jusqu_au` (Date),
    `echeances` (Table `echeance_paiement_openlab` : `date_limite` Date, `montant` Int, `libelle` Data) ; unique
    (`apprenant`, `cours`) ; lecture `Intendant OpenLab`, `System Manager` ; aucune écriture Desk pour les autres
  - `paiement_openlab` — `dossier` (Link), `montant` (Int), `moyen` (Select `cinetpay`, `virement`), `reference`
    (Data, unique par moyen), `statut` (Select `en_attente`, `confirme`, `echoue`), `date_paiement` (Datetime),
    `auteur` (Link User)
  - `journal_paiement_openlab` — `dossier`, `acteur`, `action`, `motif` (Small Text), `avant`, `apres` (Long Text
    JSON), `horodatage` ; `on_update`/`on_trash` refusés (non modifiable), comme `Journal Note OpenLab`
  - `rappel_paiement_openlab` — `dossier`, `date_limite`, `jours_avant`, `canal`, `statut` (`envoye`, `echec`,
    `ignore`), clé unique `dossier|date_limite|jours_avant|canal` (idempotence)
- Modifier : `openlab_academy/entrypoints/install.py` — créer le rôle `Intendant OpenLab` (desk access) dans
  `after_install` et `after_migrate`
- Créer : `openlab_academy/patches/dispenser_inscriptions_existantes.py` + ligne dans `patches.txt` — un dossier
  `dispense = 1` par `LMS Batch Enrollment` existant sans dossier
- Test : `openlab_academy/tests/test_paiement_donnees_frappe.py`

- [ ] **Étape 1 : tests rouges** — tarif non multiple de 5 refusé à l'enregistrement ; journal non modifiable ; rôle
  créé ; patch : inscription existante → dossier dispensé, rejoué sans doublon ; unicité (`apprenant`, `cours`).
- [ ] **Étape 2 :** `bash docker/dev-test.sh openlab_academy.tests.test_paiement_donnees_frappe` → échec
- [ ] **Étape 3 :** DocTypes, rôle, patch
- [ ] **Étape 4 :** PASS (le banc migre via `dev-sync.sh`)
- [ ] **Étape 5 :** commit `feat(academy): données du paiement (tarifs, dossiers, paiements, journal, rappels, rôle Intendant)`

### Tâche 4 : inscription et changement de mode

**Fichiers :**
- Créer : `openlab_academy/application/paiements.py` (cas d'usage), `openlab_academy/application/ports_paiement.py`,
  `openlab_academy/infrastructure/depot_dossiers_frappe.py`, `openlab_academy/infrastructure/journal_paiement_frappe.py`,
  `openlab_academy/entrypoints/paiement.py`
- Modifier : `hooks.py` — `doc_events["LMS Batch Enrollment"] = {"before_insert": ...paiement.avant_inscription, "after_insert": ...paiement.apres_inscription}`
- Test : `openlab_academy/tests/test_paiements.py` (cas d'usage, faux ports), `openlab_academy/tests/test_paiement_inscription_frappe.py`

**Interfaces :**
- Consomme : Tâches 1-3
- Produit (ports, `ports_paiement.py`, `Protocol`) :
  - `DepotDossiers` : `charger(apprenant: str, cours: str) -> DossierEnregistre | None`, `creer(d: NouveauDossier) -> str`,
    `remplacer_echeances(nom: str, mode: Mode, echeances: tuple[Echeance, ...]) -> None`,
    `paye(nom: str) -> int` (somme des paiements `confirme`), `fixer_delai(nom, d: date) -> None`
  - `Journal` : `__call__(dossier: str, acteur: str, action: str, avant: dict, apres: dict, motif: str = "") -> None`
  - `DossierEnregistre` (dataclass) : `nom, apprenant, cours, mode, telephone, tarif: Tarif, debut: date, fin: date, dossier: Dossier`
- Produit (cas d'usage, `paiements.py`) :
  - `OuvrirDossier(depot, tarifs, reglages, aujourd_hui).executer(apprenant, cours, cohorte, debut, fin) -> str`
    — lève `InscriptionTardive` si `not inscription_permise`, `TarifAbsent` si le parcours n'a pas de tarif ; crée le
    dossier avec mode `une_fois` provisoire et seule l'échéance des frais (le choix du mode se fait à la page de
    paiement, avant tout accès)
  - `ChoisirMode(depot, journal, aujourd_hui).executer(apprenant, cours, mode, telephone) -> tuple[Echeance, ...]`
    — `replanifier` avec le déjà-payé ; journal `mode` (avant/après) ; téléphone validé (`+225` et 10 chiffres, ou
    E.164 générique)
- [ ] **Étape 1 : tests rouges** — inscription crée un dossier avec prix figés ; tarif modifié ensuite sans effet sur le
  dossier ; inscription 2 mois + 1 jour après le début refusée (`frappe.ValidationError` côté hook, message « Les
  inscriptions à cette cohorte sont closes ») ; changement de mode replanifie et journalise acteur et avant/après ;
  téléphone invalide refusé ; parcours sans tarif → inscription refusée avec message clair.
- [ ] **Étape 2 :** pytest (cas d'usage) + `dev-test.sh` (Frappe) → échec
- [ ] **Étape 3 :** implémenter
- [ ] **Étape 4 :** PASS
- [ ] **Étape 5 :** commit `feat(academy): dossier de paiement ouvert à l'inscription, choix et changement de mode`

### Tâche 5 : paiement en ligne CinetPay

**Fichiers :**
- Créer : `openlab_academy/infrastructure/cinetpay.py`
- Modifier : `application/paiements.py`, `application/ports_paiement.py`, `entrypoints/paiement.py`
- Test : `openlab_academy/tests/test_cinetpay.py` (HTTP simulé), `openlab_academy/tests/test_paiements.py`,
  `openlab_academy/tests/test_paiement_cinetpay_frappe.py`

**Interfaces :**
- Produit :
  - Port `Passerelle` : `disponible() -> bool`, `initier(transaction: str, montant: int, description: str, client: Client, retour: str, notification: str) -> str`
    (URL de paiement), `verifier(transaction: str) -> Verification` avec
    `Verification(statut: Literal["confirme", "echoue", "en_attente"], montant: int)`
  - `PasserelleCinetPay(site_id, api_key, secret)` : `initier` → `POST https://api-checkout.cinetpay.com/v2/payment`
    (`currency="XOF"`, `channels="ALL"`, `lang="fr"`) ; `verifier` → `POST https://api-checkout.cinetpay.com/v2/payment/check`
    (`ACCEPTED` → confirme, `REFUSED`/`CANCELED` → echoue, sinon en_attente) ; `jeton_valide(corps: dict, x_token: str) -> bool`
    (HMAC SHA-256 de la concaténation documentée des champs `cpm_*`, clé secrète, comparaison à temps constant) ;
    délai 15 s, pas de redirection suivie, aucune clé dans les erreurs (même règle que `correcteur_ia.py`)
  - `InitierPaiement(depot, passerelle, aujourd_hui).executer(apprenant, cours) -> str` — montant = part due de
    la prochaine échéance non couverte (au moins les frais), arrondie au multiple de 5 supérieur (un paiement partiel
    antérieur peut laisser un reste non multiple de 5) ; crée un `Paiement OpenLab` `en_attente` de référence
    `OLA-<dossier>-<horodatage>` ; `PaiementIndisponible` si la passerelle n'est pas configurée
  - `ConfirmerPaiement(depot, passerelle, journal).executer(transaction: str) -> None` — idempotent ; enregistre le
    **montant vérifié** ; ignore une transaction inconnue
  - API : `paiement_api.notification_cinetpay()` (`allow_guest=True`, POST seulement, `x-token` vérifié puis
    `verifier`), `paiement_api.retour_cinetpay()` (GET, redirige vers `/espace/paiement/<cours>` sans rien valider)
- [ ] **Étape 1 : tests rouges** — corps d'initiation exact (XOF, montant, transaction, URLs) ; `x-token` faux →
  rien ; même notification deux fois → un seul paiement confirmé ; montant vérifié 100 000 pour 187 500 attendus →
  paiement de 100 000 et dossier toujours en retard ; statut `REFUSED` → `echoue` ; passerelle non configurée →
  `PaiementIndisponible` ; aucune clé dans le texte d'une exception réseau.
- [ ] **Étape 2 :** échec
- [ ] **Étape 3 :** implémenter
- [ ] **Étape 4 :** PASS
- [ ] **Étape 5 :** commit `feat(academy): paiement CinetPay (initiation, notification vérifiée et idempotente)`

### Tâche 6 : virements et délais (intendant, administrateur)

**Fichiers :**
- Modifier : `application/paiements.py`, `entrypoints/paiement_api.py` (créer)
- Test : `openlab_academy/tests/test_paiements.py`, `openlab_academy/tests/test_paiement_api_frappe.py`

**Interfaces :**
- Produit :
  - `EnregistrerVirement(depot, journal).executer(acteur, dossier, montant: int, reference: str, date_paiement: date, motif: str) -> None`
    — montant > 0, référence obligatoire et unique ; paiement `virement` `confirme`, `auteur = acteur` ; journal
  - `AccorderDelai(depot, journal, aujourd_hui).executer(acteur, dossier, jusqu_au: date, motif: str) -> None` —
    date > aujourd'hui, motif obligatoire ; journal (avant/après)
  - API (rôles `Intendant OpenLab` ou `System Manager`, sinon `frappe.PermissionError`) :
    `enregistrer_virement(dossier, montant, reference, date_paiement, motif)`, `accorder_delai(dossier, jusqu_au, motif)` ;
    mêmes protections que `evaluation_api` (`_api`, débit limité, POST)
- [ ] **Étape 1 : tests rouges** — apprenant → refus ; intendant enregistre → dossier débloqué, journal avec l'acteur ;
  référence en double → refus ; délai passé ou sans motif → refus ; administrateur et intendant journalisés chacun
  sous leur nom.
- [ ] **Étape 2-4 :** échec, implémentation, PASS
- [ ] **Étape 5 :** commit `feat(academy): virements et délais enregistrés par l'intendant ou l'administrateur, journalisés`

### Tâche 7 : blocage par parcours

**Fichiers :**
- Créer : `openlab_academy/application/acces_parcours.py`, `openlab_academy/public/js/paiement.js`
- Modifier : `entrypoints/lms.py` (`get_lesson`), `entrypoints/http.py` (`before_request`), `infrastructure/habillage.py`
  (injecte aussi `<script src="/assets/openlab_academy/js/paiement.js" defer>`), `hooks.py` (`before_request`)
- Test : `openlab_academy/tests/test_acces_parcours.py`, `openlab_academy/tests/test_blocage_frappe.py`,
  `openlab_academy/tests/test_habillage.py`

**Interfaces :**
- Produit :
  - `class ParcoursBloque(frappe.ValidationError)` dans `entrypoints/lms.py`, message « Paiement requis », avec
    `redirection = "/espace/paiement/<cours>"`
  - `parcours_bloque(apprenant: str, cours: str, aujourd_hui: date) -> bool` (`acces_parcours.py`, via le port de
    dépôt) — faux sans dossier, faux pour les rôles jamais bloqués
  - `get_lesson` : lève `ParcoursBloque` avant toute lecture si bloqué
  - `before_request` : requête GET HTML sur `/lms/courses/<cours>` ou `/lms/courses/<cours>/learn/...` d'un apprenant
    bloqué → redirection 302 vers `/espace/paiement/<cours>` ; rien sur `/api`, `/assets`, `/espace`, `/login`,
    `/logout`
  - `paiement.js` : enveloppe `window.fetch` ; réponse JSON avec `exc_type == "ParcoursBloque"` → `location.assign` vers
    la redirection
- [ ] **Étape 1 : tests rouges** — bloqué → `get_lesson` lève `ParcoursBloque` (point de vigilance 5) ; parcours à jour
  ouvert pendant qu'un autre est bloqué ; page de cours bloquée redirigée, `/espace/paiement/...` et `/logout` jamais ;
  correcteur inscrit en retard non bloqué ; habillage injecte le script une seule fois.
- [ ] **Étape 2-4 :** échec, implémentation, PASS
- [ ] **Étape 5 :** commit `feat(academy): parcours bloqué redirigé vers le paiement, les autres restent ouverts`

### Tâche 8 : rappels sur trois canaux

**Fichiers :**
- Créer : `openlab_academy/infrastructure/canaux.py` (`CanalEmail`, `CanalSms`, `CanalWhatsApp`),
  `openlab_academy/application/rappels.py`
- Modifier : `entrypoints/paiement.py` (`envoyer_rappels`), `hooks.py`
  (`scheduler_events["cron"]["0 8 * * *"] = ["openlab_academy.entrypoints.paiement.envoyer_rappels"]`)
- Test : `openlab_academy/tests/test_rappels.py`, `openlab_academy/tests/test_canaux.py`,
  `openlab_academy/tests/test_rappels_frappe.py`

**Interfaces :**
- Produit :
  - Port `Canal` : `nom: str`, `disponible() -> bool`, `envoyer(destinataire: Destinataire, message: Message) -> None`
    (`Destinataire(email, telephone, nom)`, `Message(sujet, texte, parametres: tuple[str, ...])`)
  - `CanalEmail` : `frappe.sendmail` (file d'attente Frappe), toujours disponible
  - `CanalSms` : API SMS Orange (OAuth `client_credentials` sur `sms_url_jeton`, puis
    `POST https://api.orange.com/smsmessaging/v1/outbound/tel%3A%2B<expediteur>/requests`) ; disponible si les trois
    champs SMS sont saisis
  - `CanalWhatsApp` : `POST https://graph.facebook.com/v21.0/<phone_id>/messages`, message `template` (`whatsapp_modele`,
    langue `fr`, paramètres : nom, montant, date) ; disponible si phone_id, jeton et modèle sont saisis
  - `EnvoyerRappels(depot, canaux, registre, aujourd_hui).executer() -> int` — pour chaque dossier non dispensé,
    `rappels_dus` ; un envoi par (dossier, date limite, jours, canal) au plus (`Rappel Paiement OpenLab`) ; l'échec
    d'un canal est journalisé `echec` et n'empêche pas les autres ; canal indisponible → `ignore`
  - Texte : « Rappel OpenLab Academy : <montant> FCFA à régler au plus tard le <JJ/MM/AAAA> pour le parcours
    <titre>. Payer : <URL du site>/espace/paiement/<cours> »
- [ ] **Étape 1 : tests rouges** — J-7, J-3, J-1 envoyés une fois chacun même si la tâche tourne deux fois ; SMS en
  erreur → e-mail et WhatsApp partent, `echec` consigné ; canal non configuré → `ignore` ; corps HTTP SMS et WhatsApp
  exacts ; aucun jeton dans une erreur.
- [ ] **Étape 2-4 :** échec, implémentation, PASS
- [ ] **Étape 5 :** commit `feat(academy): rappels J-7, J-3, J-1 par e-mail, SMS et WhatsApp, idempotents`

### Tâche 9 : API de lecture (apprenant, intendant, administrateur)

**Fichiers :**
- Modifier : `entrypoints/paiement_api.py`
- Créer : `openlab_academy/infrastructure/tableaux_paiement_frappe.py` (requêtes agrégées)
- Test : `openlab_academy/tests/test_paiement_api_frappe.py`

**Interfaces :**
- Produit (whitelistées, GET) :
  - `mon_dossier(cours) -> {cours, titre, mode, telephone, tarif: {frais_inscription, une_fois, deux_tranches, mensuel}, echeances: [{date_limite, montant, libelle, couverte}], paye, reste, statut, prochaine: {date_limite, montant} | None, paiement_en_ligne: bool}`
    — seulement son propre dossier
  - `choisir_mode(cours, mode, telephone)` (POST), `payer(cours) -> {url}` (POST)
  - `intendance(parcours?, cohorte?, mode?, statut?, du?, au?) -> {indicateurs: {encaisse_mois, encours_30j, en_retard: {montant, apprenants}, bloques}, lignes: [{dossier, apprenant, nom, parcours, mode, paye, total, prochaine, statut}]}`
  - `fiche(dossier) -> {..., paiements: [...], rappels: [...], journal: [{acteur, action, motif, horodatage, avant, apres}]}`
  - `export_intendance(...)` → fichier `.xlsx` (`frappe.utils.xlsxutils.make_xlsx`)
  - `resume() -> {encaisse_mois, evolution_pct, taux_recouvrement, retards, bloques, par_parcours: [{parcours, inscrits, encaisse, reste}], modes: {une_fois, deux_tranches, mensuel}, dernieres_actions: [5 dernières lignes du journal]}`
    — `resume`, `intendance`, `fiche`, `export` : `Intendant OpenLab` ou `System Manager` ; tout autre rôle refusé
- [ ] **Étape 1 : tests rouges** — apprenant ne lit que son dossier ; aucune clé ni secret dans les réponses ;
  indicateurs exacts sur un jeu de 3 dossiers (à jour, en retard, soldé) ; filtres ; export lisible ; résumé et vue
  détaillée refusés à un apprenant et à un correcteur.
- [ ] **Étape 2-4 :** échec, implémentation, PASS
- [ ] **Étape 5 :** commit `feat(academy): API des paiements (dossier apprenant, vue intendant, résumé, export)`

### Tâche 10 : écran apprenant « Mes paiements »

**Fichiers :**
- Créer : `frontend/src/domaine/paiement.ts` (+ test), `frontend/src/application/paiement.ts` (+ test),
  `frontend/src/interface/ecrans/Paiement.vue` (+ test)
- Modifier : `frontend/src/infrastructure/frappe/depots.ts`, `schemas.ts`, `frontend/src/application/ports.ts`,
  `frontend/src/interface/routeur.ts` (route `/paiement/:cours`, titre « Mes paiements »), `frontend/src/test/faux-ports.ts`

**Interfaces :**
- Produit : `formaterXof(montant: number): string` (« 187 500 FCFA », espaces fines insécables) ; `libelleStatut`;
  cas d'usage `chargerDossier`, `choisirMode`, `payer` (redirection vers l'URL CinetPay)
- Écran : bandeau d'état (à jour / en retard / soldé), choix du mode en trois cartes (prix global et calendrier de
  chaque mode), téléphone, échéancier, bouton « Payer <montant> » ; si le paiement en ligne n'est pas configuré :
  instructions de virement et mention « paiement en ligne bientôt disponible ». Design soigné dans la charte
  (`style.css`, composants existants `EnTete`, `Puce`).
- [ ] **Étape 1 : tests rouges** — format XOF ; trois cartes avec les prix ; changement de mode → appel puis échéancier
  rafraîchi ; bouton payer → redirection ; paiement indisponible → instructions de virement.
- [ ] **Étape 2-4 :** `npm test` échec, implémentation, PASS ; `npm run lint && npm run typecheck`
- [ ] **Étape 5 :** commit `feat(academy): écran Mes paiements (mode, échéancier, paiement)`

### Tâche 11 : écrans Intendance et Finances

**Fichiers :**
- Créer : `frontend/src/interface/ecrans/Intendance.vue`, `Finances.vue`, `frontend/src/interface/composants/Indicateur.vue`,
  `FichePaiement.vue` (+ tests)
- Modifier : `routeur.ts` (`/intendance` « Intendance », `/finances` « Finances »), dépôts, ports, faux ports
- Contenu : celui des maquettes validées (spec §6) ; design soigné : indicateurs en cartes, tableau trié et filtrable,
  puces de statut colorées accessibles (contraste AA), fiche en panneau latéral, formulaires « Enregistrer un
  virement » et « Accorder un délai » avec motif obligatoire, export Excel.
- [ ] **Étape 1 : tests rouges** — filtres appliqués à l'API ; fiche affiche journal avec l'acteur ; formulaire de
  virement refuse un montant vide et la référence manquante ; Finances affiche les trois indicateurs et le tableau par
  parcours.
- [ ] **Étape 2-4 :** échec, implémentation, PASS ; lint, types, build
- [ ] **Étape 5 :** commit `feat(academy): écrans Intendance et Finances`

### Tâche 12 : vérification de bout en bout et documentation

**Fichiers :**
- Modifier : `apps/openlab_academy/README.md` (section « Paiement » : réglages, rôles, rappels, CinetPay sandbox)
- [ ] **Étape 1 :** `bash docker/dev-test.sh` → `OK`, couverture ≥ 99 % ; `npm test -- --coverage`, `npm run lint`,
  `npm run typecheck`, `npm run build` → verts
- [ ] **Étape 2 :** sur le banc (http://lms.localhost:8000) : tarif saisi par un intendant ; inscription d'un apprenant
  → redirection vers « Mes paiements » ; choix du mode ; virement enregistré par l'intendant → parcours ouvert ;
  date simulée au 11 → parcours bloqué, autre parcours ouvert ; rappel e-mail visible dans la file d'e-mails ;
  journal lisible dans la fiche. Si des clés CinetPay de test existent, un paiement en sandbox.
- [ ] **Étape 3 :** commit `docs(academy): paiement des parcours (réglages, rôles, rappels)` ; publication
  `git subtree split --prefix=Openlab_Academy -b academy-main && git push academy academy-main:develop` ; CI verte.
