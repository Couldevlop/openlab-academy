# Parcours de lancement « IA agentique » et phase de lancement — plan de réalisation

> **Pour l'exécutant :** suivre ce plan tâche par tâche (superpowers:subagent-driven-development ou
> superpowers:executing-plans). Étapes en cases à cocher (`- [ ]`).

**But :** publier le parcours gratuit « IA agentique : comprendre, concevoir et maîtriser les agents IA », ouvert un
mois (fenêtre = dates de sa cohorte), fermé et retiré du catalogue ensuite, premier et mis en avant ; et une phase de
lancement, réglable par l'administrateur, qui cache les autres parcours aux apprenants et aux visiteurs.

**Architecture :** trois nouvelles clés du fichier de parcours (`gratuit`, `acces_limite_a_la_cohorte`,
`mise_en_avant`) portées par le domaine et écrites par la publication (case « Parcours gratuit (MOOC) », case
« Accès limité aux dates de la cohorte », `featured` du LMS). La visibilité n'est **jamais stockée** : à chaque requête,
`application/visibilite.py` calcule un refus (`FERME` hors fenêtre, `CACHE` pendant la phase de lancement) depuis les
dates de la cohorte et l'écran de réglages, comme le blocage pour paiement ; les points d'entrée existants
(`before_request`, surcharges whitelistées, `has_permission`, `permission_query_conditions`, `before_insert` des
inscriptions) l'appliquent, plus de nouvelles surcharges des listes du LMS. Seul le retrait du catalogue après la fin
écrit en base (`published = 0`, tâche quotidienne). La vidéo d'une leçon vit dans un champ personnalisé de
`Course Lesson`, hors du contenu republié, et est insérée en tête du contenu servi par `get_lesson`.

**Pile :** Frappe v15 + LMS, Python 3.11.

**Spec :** `docs/specs/2026-10-29-academy-parcours-ia-agentique-design.md`

## Contraintes globales

- Ne modifier ni `apps/frappe` ni `apps/lms` : surcharges par hooks, `override_whitelisted_methods`, champs
  personnalisés, `doc_events`.
- Architecture hexagonale : `domain/` n'importe jamais `frappe` ; sécurité OWASP au premier plan (aucune URL de
  redirection fournie par le client, noms de parcours encodés en un seul segment, liens vidéo filtrés).
- Rôles jamais bloqués ni masqués (agents) : `ROLES_NON_BLOQUES` de `entrypoints/lms.py` (`System Manager`,
  `Moderator`, `Course Creator`, `Batch Evaluator`, `Intendant OpenLab`). Le visiteur (`Guest`) **est** concerné par la
  fermeture et le masquage (contrairement au blocage pour paiement).
- Fenêtre : `debut = O`, `fin = O + 1 mois calendaire` (jour ramené au dernier jour du mois s'il n'existe pas) ;
  ouverte de `debut` 00:00 à `fin` 23:59:59 incluses, date du site (`getdate(nowdate())`, Abidjan = UTC).
  `O` initial = réglage `ouverture_lancement`, vide ou passé → date du jour.
- Charge du parcours : 7 modules × 3 h + capstone 3 h = **24 h** ; `projets_par_portfolio: 0` ; quiz de **5** questions.
- Parcours gratuit : aucun tarif, échéancier, rappel ni blocage pour paiement (mécanisme MOOC existant).
- Textes d'interface en français dans `_()` avec leur entrée dans `openlab_academy/translations/en.csv` (le test
  `test_traductions.test_toute_chaine_traduisible_a_son_anglais` l'exige) ; libellés des nouveaux champs et doctypes
  ajoutés aussi à `en.csv`. Contenu du parcours (YAML, cohorte) en français, jamais dans `_()`.
- Tests : TDD ; `bash docker/dev-test.sh openlab_academy.tests.<module>` depuis `D:\OPENLAB\Openlab_Academy` (un
  module), `bash docker/dev-test.sh` (suite complète, couverture back ≥ 99 %) ; verts **sur un site neuf** (CI) ;
  ne pas dépendre de l'état du banc.
- Machine à 8 Go : **ne jamais démarrer la pile `ol-academy` pendant les tests** du banc de dev, et inversement ;
  commandes longues en arrière-plan ; une commande tuée faute de mémoire se relance une fois.
- Git : `git add` par chemins explicites (jamais `-A` ni `.`) ; commits conventionnels en français
  (`feat(academy): …`), **sans aucune ligne d'attribution ni mention d'outil ou d'assistant**, nulle part. Travail sur
  la branche `feat/academy-bilingue`, commits séparés de ceux du plan bilingue.

## Points de vigilance (à épingler par un test)

1. **Leçon d'un parcours fermé ou caché lue par l'API** (`get_lesson`, `frappe.client.get` sur `Course Lesson`, liste de
   leçons, questions d'un quiz) par un apprenant **et par un visiteur** : refusée, aucun contenu ni lien vidéo renvoyé
   (Tâche 9).
2. **Agents sur un parcours fermé ou caché** (formateur `Course Creator`, correcteur `Batch Evaluator`, intendant,
   modérateur, administrateur) : pages, API, catalogue et inscription inchangés (Tâches 9, 10, 11).
3. **Vidéo ajoutée dans la console puis `bench migrate`** sur un parcours sans inscrit (republication par
   `remplacer`, qui supprime et recrée les leçons) : la vidéo est toujours là (Tâche 4).
4. **Bord de fenêtre** : le jour `fin` reste ouvert toute la journée, fermé le lendemain dès 00:00 (Abidjan) ;
   `O = 2027-01-31` → `fin = 2027-02-28` (Tâches 2 et 9).
5. **Phase de lancement décochée** : tous les parcours reviennent au catalogue, à l'accueil, à la recherche, à
   l'inscription et à leurs pages, sans autre action ni donnée modifiée ; recochée, ils disparaissent de nouveau
   (Tâches 9, 10, 11).

---

### Tâche 1 : clés du fichier de parcours (gratuit, accès limité, mise en avant, sans portfolio)

**Fichiers :**
- Modifier : `openlab_academy/domain/parcours.py`, `openlab_academy/infrastructure/yaml_source.py`
- Test : `openlab_academy/tests/test_domaine.py`, `openlab_academy/tests/test_yaml_source.py`,
  `openlab_academy/tests/fabriques.py` (si besoin)

**Interfaces :**
- Produit :
  - `Parcours` gagne `gratuit: bool = False`, `acces_limite_a_la_cohorte: bool = False`, `mise_en_avant: bool = False`
    (après les champs existants, valeurs par défaut : aucun parcours existant ne change).
  - YAML : clés de premier niveau `gratuit`, `acces_limite_a_la_cohorte`, `mise_en_avant` (booléens YAML stricts,
    absentes = `false`) ; `portfolio` facultatif (absent ou `[]`) **seulement** si `projets_attendus == 0` (sinon le
    message actuel « portfolio manquant »).

- [ ] **Step 1 : tests** —
  - `test_yaml_source.py` : `test_cles_de_lancement_lues` (`gratuit: true`, `acces_limite_a_la_cohorte: true`,
    `mise_en_avant: true` → les trois attributs `True`) ; `test_cles_de_lancement_absentes_valent_faux` ;
    `test_cle_de_lancement_non_booleenne_refusee` (`gratuit: 1` et `gratuit: "oui"` → `FormatInvalide` contenant
    `"gratuit doit être un booléen"`) ;
    `test_sans_portfolio_si_zero_projet` (`parametres: {projets_par_portfolio: 0, heures_par_module: 3}`, pas de clé
    `portfolio` → `portfolio == ()`, `charge_horaire()` = modules × 3 + capstone) ;
    `test_portfolio_vide_refuse_si_projets_attendus` (`portfolio: []` sans paramètre → `FormatInvalide`
    « portfolio manquant »).
  - `test_domaine.py` : `test_drapeaux_par_defaut_faux` sur `fabriques.parcours()`.
- [ ] **Step 2 : lancer** `bash docker/dev-test.sh openlab_academy.tests.test_yaml_source` → FAIL.
- [ ] **Step 3 : implémenter** — dans `_Lecteur.parcours`, lire les trois clés par une méthode
  `booleen(d: dict, cle: str) -> bool` (`isinstance(v, bool)`, absente → `False`) ; le portfolio est exigé seulement si
  `self.parametres(d)["projets_attendus"] > 0`.
- [ ] **Step 4 : lancer** `test_yaml_source` puis `test_domaine` → PASS.
- [ ] **Step 5 : commit** `feat(academy): clés gratuit, accès limité à la cohorte et mise en avant des parcours`.

### Tâche 2 : fenêtre d'accès et phase de lancement (domaine et cas d'usage)

**Fichiers :**
- Créer : `openlab_academy/domain/fenetre.py`, `openlab_academy/domain/lancement.py`,
  `openlab_academy/application/visibilite.py`
- Test : `openlab_academy/tests/test_fenetre.py`, `openlab_academy/tests/test_visibilite.py`

**Interfaces :**
- Produit :
  - `domain/fenetre.py` : `class FenetreInvalide(ValueError)` ; `@dataclass(frozen=True) class Fenetre: debut: date;
    fin: date` (`fin < debut` → `FenetreInvalide`) avec `ouverte(jour: date) -> bool` (`debut <= jour <= fin`),
    `terminee(jour: date) -> bool` (`jour > fin`) ; `un_mois_apres(d: date) -> date` ;
    `date_ouverture(reglee: date | None, aujourd_hui: date) -> date` (`None` ou `< aujourd_hui` → `aujourd_hui`).
  - `domain/lancement.py` : `@dataclass(frozen=True) class PhaseLancement: active: bool = True;
    visibles: frozenset[str] = frozenset()` avec `cache(cours: str) -> bool` (`active and cours not in visibles`).
  - `application/visibilite.py` :
    - `class Refus(str, Enum): FERME = "ferme"; CACHE = "cache"`
    - `class SourceVisibilite(Protocol)` : `phase() -> PhaseLancement` ; `limite(cours: str) -> bool` ;
      `fenetre(cours: str) -> Fenetre | None` ; `tous_les_cours() -> tuple[str, ...]` ;
      `cours_limites_publies() -> tuple[str, ...]`
    - `class Visibilite: __init__(self, source: SourceVisibilite, aujourd_hui: Callable[[], date])` ;
      `refus(self, cours: str, agent: bool) -> Refus | None` (agent → `None` ; `CACHE` prime sur `FERME` ; parcours
      limité sans cohorte → `FERME`) ; `refuses(self, agent: bool) -> frozenset[str]` (tous les cours refusés, pour
      filtrer les listes) ; `echus(self) -> tuple[str, ...]` (parcours limités publiés dont la fenêtre est terminée).
    - `PREFIXE_FERME = "/parcours-ferme/"`, `CATALOGUE = "/lms/courses"`,
      `redirection(refus: Refus, cours: str) -> str` (`FERME` → `PREFIXE_FERME + quote(cours, safe="")`, `CACHE` →
      `CATALOGUE`).

- [ ] **Step 1 : tests** —
  - `test_fenetre.py` : `un_mois_apres(date(2026, 11, 2)) == date(2026, 12, 2)` ;
    `un_mois_apres(date(2027, 1, 31)) == date(2027, 2, 28)` ; `un_mois_apres(date(2028, 1, 31)) == date(2028, 2, 29)` ;
    `un_mois_apres(date(2026, 12, 15)) == date(2027, 1, 15)` ; fenêtre 2026-11-02 → 2026-12-02 : fermée le 2026-11-01,
    ouverte le 2026-11-02 et le 2026-12-02, fermée et `terminee` le 2026-12-03 ; `Fenetre(d2, d1)` avec `d2 > d1` →
    `FenetreInvalide` ; `date_ouverture(None, j) == j`, `date_ouverture(j - 1 jour, j) == j`,
    `date_ouverture(j + 10 jours, j) == j + 10 jours`.
  - `test_visibilite.py` (source factice en mémoire) : `test_agent_jamais_refuse` (caché et fermé → `None`) ;
    `test_cache_pendant_le_lancement` ; `test_phase_inactive_rien_de_cache` ; `test_cache_prime_sur_ferme` ;
    `test_limite_hors_fenetre_ferme` (avant `debut` et après `fin`) ; `test_limite_sans_cohorte_ferme` ;
    `test_non_limite_jamais_ferme` ; `test_refuses_union_caches_et_fermes` ; `test_echus` (seul le parcours limité
    dont `fin < aujourd_hui` sort ; un parcours limité pas encore ouvert n'est pas échu) ;
    `test_redirection_encodee` : `redirection(Refus.FERME, "../a b?x=1#y") == "/parcours-ferme/..%2Fa%20b%3Fx%3D1%23y"`,
    `redirection(Refus.FERME, "//evil.example") == "/parcours-ferme/%2F%2Fevil.example"`,
    `redirection(Refus.CACHE, "x") == "/lms/courses"`.
- [ ] **Step 2 : lancer** les deux modules → FAIL (modules absents).
- [ ] **Step 3 : implémenter** (aucun import Frappe ; `un_mois_apres` sans `dateutil` : `calendar.monthrange`).
- [ ] **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): fenêtre d'accès d'un parcours et phase de lancement (domaine)`.

### Tâche 3 : fichier du parcours « IA agentique »

**Fichiers :**
- Créer : `openlab_academy/data/parcours/06-ia-agentique.yaml`
- Modifier : `openlab_academy/tests/test_yaml_source.py` (`test_parcours_livres_valides`)
- Test : `openlab_academy/tests/test_parcours_ia_agentique.py`

**Interfaces :**
- Produit : titre exact `IA agentique : comprendre, concevoir et maîtriser les agents IA` (constante
  `TITRE_LANCEMENT` déclarée dans `openlab_academy/domain/reglages.py` à la Tâche 6 ; ici en clair dans le test).

Contenu (à écrire fidèlement depuis le design §2, orthographe soignée, niveau du parcours AI Engineer) :
- `short_introduction` = l'accroche. `description` (HTML `<p>`) : public, objectifs 1 à 5 (liste), méthode, fil rouge,
  prérequis, non requis au départ, format (« Gratuit. Cours en vidéo, à votre rythme, sans séance en direct ; quiz,
  exercices et projet final en autonomie, projet rendu et corrigé sur la plateforme. Ouvert un mois. »).
- `tags: [IA agentique, Agents IA, Tool calling, LangGraph, MCP, A2A, Évaluation]`, `card_gradient: Violet`,
  `gratuit: true`, `acces_limite_a_la_cohorte: true`, `mise_en_avant: true`,
  `parametres: {projets_par_portfolio: 0, heures_par_module: 3}`, pas de `portfolio`.
- Un bloc par séance n'est pas requis : un seul bloc `"Programme — 7 séances et un projet final"` de 7 modules. Chaque
  module : `contenu` (points clés ci-dessous), `livrable` = étape N du fil rouge, `mise_en_situation`, `quiz` de
  5 questions (4 options, explication).

| num | title | points clés du `contenu` | `livrable` (fil rouge) |
|---|---|---|---|
| 01 | Anatomie d'un agent IA | boucle percevoir–raisonner–agir ; modèle, outils, mémoire, contrôle ; agent, chatbot, RAG et workflow ; degrés d'autonomie et limites | Étape 1 : cahier des charges de l'agent d'analyse documentaire (cas métier, sources, outils, critères de réussite) et schéma de sa boucle |
| 02 | Tool calling et boucle d'agent | schéma JSON d'un outil ; appel, résultat, réponse finale ; boucle bornée en Python sans framework ; validation des arguments ; erreurs d'outil renvoyées au modèle | Étape 2 : agent Python minimal à deux outils (recherche dans un dossier de documents, lecture d'un document), boucle bornée, erreurs gérées |
| 03 | Patterns d'orchestration | chaînage, routage, parallélisation, orchestrateur–exécutants, évaluateur–optimiseur ; ReAct et plan-and-execute ; choisir un framework (LangGraph) | Étape 3 : orchestration en graphe recherche → vérification → synthèse |
| 04 | État, mémoire et reprise sur erreur | état typé ; mémoire courte et longue ; checkpoints et reprise ; idempotence, nouvelles tentatives avec délai croissant ; validation humaine | Étape 4 : état persistant, checkpoint et reprise après l'échec d'un outil |
| 05 | MCP et interopérabilité | Model Context Protocol : serveur, client, outils, ressources, prompts, transports stdio et HTTP ; sécurité d'un serveur MCP ; A2A : carte d'agent, tâches, usages | Étape 5 : outils du fil rouge exposés par un serveur MCP et consommés par l'agent |
| 06 | Architectures multi-agents et A2A | superviseur, hiérarchie, réseau, transfert entre agents ; rôles chercheur, vérificateur, rédacteur ; coût et cas où un seul agent suffit | Étape 6 : collaboration chercheur–vérificateur–rédacteur |
| 07 | Sécurité, évaluation et observabilité | injection de prompt directe et indirecte ; moindre privilège des outils ; jeux d'évaluation, LLM juge ; traces, coût par exécution, budget | Étape 7 : suite d'évaluations, traces, budget de coût et garde-fous |

- `capstone` : `titre: Projet final et revue technique`, `duree_h: 3`, `niveau: autonome`, `contexte` = le fil rouge
  complet rendu sur la plateforme, la revue technique étant le retour de correction ; `objectifs` = les 5 objectifs de
  la formation ; `fonctionnalites` (outils, vérification des résultats, synthèse argumentée avec sources citées,
  reprise sur erreur, serveur MCP) ; `stack: [Python, LangGraph, SDK MCP]` ; `criteres_acceptation` (l'agent cite ses
  sources, une erreur d'outil ne l'arrête pas, les évaluations passent, le coût d'une exécution est mesuré) ;
  `exigences_specifiques: []` ; `livrables: [Dépôt Git, README, Rapport de traces et de coût]`.

- [ ] **Step 1 : tests** — `test_parcours_ia_agentique.py` : charge `PARCOURS_DIR`, trouve le parcours par son titre ;
  `gratuit`, `acces_limite_a_la_cohorte`, `mise_en_avant` vrais ; 7 modules `01`…`07` dans l'ordre du tableau ;
  chaque module a 5 questions et une mise en situation non vide ; chaque `livrable` commence par `f"Étape {n} :"` ;
  `portfolio == ()` ; `heures_par_module == 3` ; `charge_horaire() == 24` ; `capstone.titre == "Projet final et
  revue technique"` ; aucun texte ne contient `TODO` ni `…`. `test_parcours_livres_valides` : 5 parcours complets,
  portfolio de 10 pour tous sauf celui-ci.
- [ ] **Step 2 : lancer** → FAIL (fichier absent).
- [ ] **Step 3 : écrire le YAML** (options contenant « : » entre guillemets).
- [ ] **Step 4 : lancer** `test_parcours_ia_agentique` et `test_yaml_source` → PASS.
- [ ] **Step 5 : commit** `feat(academy): parcours de lancement « IA agentique »`.

### Tâche 4 : publication des drapeaux et emplacement vidéo préservé

**Fichiers :**
- Modifier : `openlab_academy/infrastructure/depot_frappe.py`, `openlab_academy/entrypoints/install.py`,
  `openlab_academy/translations/en.csv`
- Créer : `openlab_academy/infrastructure/visibilite_frappe.py` (constantes seulement à ce stade)
- Test : `openlab_academy/tests/test_depot_frappe.py`, `openlab_academy/tests/test_installation.py`

**Interfaces :**
- Consomme : `Parcours.gratuit|acces_limite_a_la_cohorte|mise_en_avant` (Tâche 1).
- Produit :
  - `visibilite_frappe.CHAMP_LIMITE = "acces_limite_cohorte"` (Check sur `LMS Course`, libellé « Accès limité aux
    dates de la cohorte », niveau de droits 1 = administrateur, comme `CHAMP_GRATUIT`) ;
    `visibilite_frappe.CHAMP_VIDEO = "video_lecon"` (Attach sur `Course Lesson`, libellé « Vidéo de la leçon »,
    description « Lien YouTube, Vimeo ou fichier vidéo ; affichée en tête de la leçon. », après `title`).
  - `install.preparer_champs_lancement() -> None` : crée ou remet à jour ces deux champs (même schéma que
    `preparer_parcours_gratuits`), appelé dans `after_install` et `after_migrate` **avant** `seed.run`.
  - `DepotFrappe._champs` : `CHAMP_LIMITE` = `int(p.acces_limite_a_la_cohorte)` toujours ; `CHAMP_GRATUIT = 1` et
    `featured = 1` **seulement** si la clé est vraie (absente : la décision de l'administrateur n'est pas écrasée) ;
    rien de cela pour une `Annonce`.
  - `DepotFrappe.completer` applique aussi ces drapeaux (parcours avec inscrits), contenu intact.
  - `DepotFrappe.remplacer` : relève `{titre de leçon: video_lecon}` des leçons du parcours **avant** `_purger` et le
    réécrit sur la leçon recréée de même titre (`_nouvelle_lecon(..., video: str = "")`).

- [ ] **Step 1 : tests** — `test_depot_frappe.py` :
  - `test_drapeaux_publies` : parcours `gratuit`/`acces_limite`/`mise_en_avant` → `parcours_gratuit == 1`,
    `acces_limite_cohorte == 1`, `featured == 1`.
  - `test_drapeaux_absents_n_ecrasent_pas_l_administrateur` : cours publié, `featured` et `parcours_gratuit` mis à 1 à
    la main, republication sans les clés → toujours 1 ; `acces_limite_cohorte` remis à 0.
  - `test_video_preservee_a_la_republication` : `video_lecon = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"` sur la
    leçon `01 · …`, republication sans inscrit (`remplacer`) → nouvelle leçon (autre `name`) de même titre avec la même
    vidéo ; une leçon sans vidéo reste sans vidéo.
  - `test_completer_applique_les_drapeaux` : parcours avec un inscrit → drapeaux écrits, leçons intactes.
  - `test_installation.py` : `test_champs_de_lancement_crees` (deux champs, `permlevel` 1 pour `acces_limite_cohorte`,
    idempotent).
- [ ] **Step 2 : lancer** `test_depot_frappe` et `test_installation` → FAIL.
- [ ] **Step 3 : implémenter ; ajouter libellés et description à `en.csv`.**
- [ ] **Step 4 : lancer** → PASS ; puis `test_traductions` → PASS.
- [ ] **Step 5 : commit** `feat(academy): drapeaux de lancement publiés et vidéo des leçons conservée`.

### Tâche 5 : vidéo affichée en tête de la leçon

**Fichiers :**
- Modifier : `openlab_academy/infrastructure/editorjs.py`, `openlab_academy/entrypoints/lms.py` (`get_lesson`)
- Test : `openlab_academy/tests/test_editorjs.py`, `openlab_academy/tests/test_video_lecon_frappe.py`

**Interfaces :**
- Consomme : `CHAMP_VIDEO` (Tâche 4).
- Produit : `editorjs.bloc_video(url: str | None) -> dict | None` — bloc Editor.js du format que produit l'éditeur de
  leçon du LMS (le vérifier dans `apps/lms/frontend/src/components/UploadPlugin.vue`, `VideoBlock.vue` et
  `utils/upload.js` / `utils/video.ts` du conteneur) : YouTube (`youtube.com/watch?v=<id>`, `youtu.be/<id>`, id
  `[A-Za-z0-9_-]{11}`) et Vimeo (`vimeo.com/<chiffres>`) → bloc d'intégration ; fichier `/files/…` ou
  `https://…` finissant par `.mp4`, `.webm`, `.ogg` → bloc de fichier vidéo ; tout le reste (`javascript:`, `http:`,
  `data:`, chemin relatif, autre domaine en intégration) → `None`. `get_lesson` insère ce bloc en tête de
  `details["content"]` (JSON Editor.js) quand il existe, sans écrire en base.

- [ ] **Step 1 : tests** — `test_editorjs.py` : les cas acceptés ci-dessus et les refus `"javascript:alert(1)"`,
  `"http://exemple.ci/v.mp4"`, `"data:video/mp4;base64,AA"`, `"https://www.youtube.com/watch?v=<script>"`, `""`,
  `None` → `None`. `test_video_lecon_frappe.py` : `test_lecon_avec_video_commence_par_le_bloc`,
  `test_lecon_sans_video_inchangee` (contenu identique à `lms_utils.get_lesson`), `test_lien_refuse_ignore` (contenu
  inchangé, aucune erreur).
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): vidéo de la leçon affichée en tête du contenu`.

### Tâche 6 : réglages de lancement

**Fichiers :**
- Créer : doctype enfant `openlab_academy/openlab_academy/doctype/parcours_lancement_openlab/` (`istable`, champ
  `cours` Link `LMS Course`, obligatoire)
- Modifier : `openlab_academy/domain/reglages.py`, `openlab_academy/infrastructure/reglages_source_frappe.py`,
  `openlab_academy/openlab_academy/doctype/reglages_openlab_academy/reglages_openlab_academy.json`,
  `openlab_academy/translations/en.csv`
- Test : `openlab_academy/tests/test_reglages.py`, `openlab_academy/tests/test_reglages_frappe.py`

**Interfaces :**
- Consomme : `PhaseLancement` (Tâche 2).
- Produit :
  - `domain/reglages.py` : `TITRE_LANCEMENT = "IA agentique : comprendre, concevoir et maîtriser les agents IA"` ;
    `Reglages.parcours_pilote` vaut désormais `TITRE_LANCEMENT` par défaut ; `Reglages.ouverture_lancement:
    date | None = None`.
  - Écran : nouvelle section « Lancement » : `phase_lancement` (Check « Phase de lancement », défaut 1, description
    « Cochée : seuls les parcours ci-dessous sont visibles des apprenants et des visiteurs. ») ; `parcours_lancement`
    (Table MultiSelect « Parcours visibles pendant le lancement », options `Parcours Lancement OpenLab`) ;
    `ouverture_lancement` (Date « Date d'ouverture du parcours de lancement ») ; `lancement_initialise` (Check, masqué,
    lecture seule). Droits inchangés : `System Manager` seul.
  - `reglages_source_frappe.phase_lancement() -> PhaseLancement` (document single en cache, `frappe.get_cached_doc`) ;
    `vers_domaine` lit `ouverture_lancement` ; `initialiser()` pose `phase_lancement = 1`.

- [ ] **Step 1 : tests** — `test_reglages.py` : `Reglages().parcours_pilote == TITRE_LANCEMENT`,
  `Reglages().ouverture_lancement is None`. `test_reglages_frappe.py` : `test_phase_lancement_lue` (case cochée et une
  ligne → `PhaseLancement(True, frozenset({nom}))`) ; `test_phase_decochee` ; `test_initialiser_coche_la_phase` ;
  `test_ouverture_lancement_vers_domaine` ; `test_ecran_reserve_a_l_administrateur` (un `Moderator` ne peut pas
  écrire le single : `frappe.PermissionError`).
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : implémenter (JSON du doctype, `bench migrate` fait par `dev-test.sh`), libellés dans `en.csv`.**
- [ ] **Step 4 : lancer** les deux modules et `test_traductions` → PASS.
- [ ] **Step 5 : commit** `feat(academy): réglages de la phase de lancement`.

### Tâche 7 : cohorte-fenêtre et migration du parcours pilote

**Fichiers :**
- Modifier : `openlab_academy/domain/cohorte.py`, `openlab_academy/application/ouvrir_cohorte.py`,
  `openlab_academy/infrastructure/depot_cohortes_frappe.py`, `openlab_academy/entrypoints/install.py`
- Test : `openlab_academy/tests/test_cohorte.py`, `openlab_academy/tests/test_cohorte_frappe.py`,
  `openlab_academy/tests/test_installation.py`

**Interfaces :**
- Consomme : `un_mois_apres`, `date_ouverture` (Tâche 2) ; `Reglages.ouverture_lancement`, `TITRE_LANCEMENT` (Tâche 6) ;
  `Parcours.acces_limite_a_la_cohorte` (Tâche 1).
- Produit :
  - `Cohorte.rythme: Rythme | None` ; `PLACES_FENETRE = 10_000` ;
    `Cohorte.fenetre(parcours: Parcours, debut: date, reglages: Reglages) -> Cohorte` : titre
    `f"Promo 1 — {parcours.title}"`, `fin = un_mois_apres(debut)`, `heure_debut = "00:00"`, `heure_fin = "23:59"`,
    fuseau des réglages, `rythme=None`, `places = PLACES_FENETRE` ; `seances` → « Accès libre, à toute heure. ».
  - `OuvrirCohorte.executer` : parcours limité → `Cohorte.fenetre(parcours, debut or date_ouverture(
    reglages.ouverture_lancement, aujourd_hui), reglages)` ; sinon comportement actuel. Idempotent par titre : une
    cohorte existante n'est jamais déplacée (les dates se changent dans la console).
  - `DepotCohortesFrappe.creer` : sans rythme, `description` « Parcours en vidéo, à votre rythme : quiz, exercices et
    projet final corrigé sur la plateforme. » et `batch_details` `<p>Ouvert du {debut} au {fin} inclus, à toute
    heure.</p>` (dates `JJ/MM/AAAA`).
  - `install.preparer_lancement(commit: bool = True) -> None`, appelé après `seed.run` dans `after_install` **et**
    `after_migrate` : si `lancement_initialise` vaut 0 → `parcours_pilote = TITRE_LANCEMENT`, `phase_lancement = 1`,
    `parcours_lancement = [cours de TITRE_LANCEMENT]`, `lancement_initialise = 1`, puis `cohorte.ouvrir_pilote`. Sinon
    rien (le choix de l'administrateur survit aux migrations). « Fondamentaux de la Data Science » et sa cohorte ne
    sont pas touchés.

- [ ] **Step 1 : tests** —
  - `test_cohorte.py` : `test_cohorte_fenetre` (début 2026-11-02 → fin 2026-12-02, titre, sans rythme, 10 000
    places) ; `test_fenetre_fin_de_mois` (2027-01-31 → 2027-02-28) ; `test_ouvrir_parcours_limite_date_du_reglage` ;
    `test_ouverture_passee_ou_vide_aujourd_hui` ; `test_cohorte_existante_jamais_deplacee`.
  - `test_cohorte_frappe.py` : `test_lot_fenetre_cree` (`start_date`, `end_date`, `start_time` 00:00:00, `end_time`
    23:59:00, `allow_self_enrollment` 1, `seat_count` 10 000, parcours rattaché).
  - `test_installation.py` : `test_after_install_configure_et_publie` mis à jour (cohorte
    `Promo 1 — IA agentique : …` créée, dates = aujourd'hui → `un_mois_apres(aujourd'hui)`) ;
    `test_migration_site_existant` (single avec `parcours_pilote = "Fondamentaux de la Data Science"`,
    `lancement_initialise = 0` → après `after_migrate(commit=False)` : pilote = `TITRE_LANCEMENT`, phase cochée, liste =
    le nouveau parcours, cohorte créée, cohorte de Fondamentaux inchangée) ;
    `test_choix_de_l_administrateur_conserve` (phase décochée, `lancement_initialise = 1`, `after_migrate` → reste
    décochée).
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer** les trois modules → PASS.
- [ ] **Step 5 : commit** `feat(academy): cohorte d'un mois du parcours de lancement, devenu parcours pilote`.

### Tâche 8 : page « Parcours fermé »

**Fichiers :**
- Créer : `openlab_academy/www/parcours-ferme.html`, `openlab_academy/www/parcours-ferme.py`
- Modifier : `openlab_academy/hooks.py` (`website_route_rules` : `{"from_route": "/parcours-ferme/<cours>",
  "to_route": "parcours-ferme"}`), `openlab_academy/translations/en.csv`
- Test : `openlab_academy/tests/test_parcours_ferme_page.py`

**Interfaces :**
- Produit : `get_context(context)` : `context.no_cache = 1` ; parcours lu par `frappe.form_dict.cours` (nom exact,
  jamais interpolé dans une requête brute) ; parcours inexistant → page générique sans titre ; variables
  `titre`, `debut`, `fin`, `a_venir: bool`. Textes : `_("Ce parcours est fermé")` (titre), `_("« {0} » était ouvert du
  {1} au {2}. Votre progression et votre certificat restent dans votre profil.")`, `_("« {0} » ouvrira le {1}.")`,
  lien `_("Voir le catalogue")` vers `/lms/courses`. Titre échappé (autoescape Jinja), charte du site
  (`openlab.css`), lisible à 375 px.

- [ ] **Step 1 : tests** — rendu en visiteur de `/parcours-ferme/<cours fermé>` : 200, contient le titre et le lien
  catalogue ; parcours au titre `<b>x</b>` → `&lt;b&gt;` ; parcours inconnu → 200 générique ; cohorte future →
  « ouvrira le ».
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : implémenter, compléter `en.csv`.** **Step 4 : lancer** avec
  `test_traductions` → PASS.
- [ ] **Step 5 : commit** `feat(academy): page « Parcours fermé »`.

### Tâche 9 : fermeture et masquage des pages, de l'API et des permissions

**Fichiers :**
- Modifier : `openlab_academy/infrastructure/visibilite_frappe.py`, `openlab_academy/entrypoints/lms.py`,
  `openlab_academy/entrypoints/http.py`, `openlab_academy/public/js/paiement.js` (les hooks `has_permission` et
  `permission_query_conditions` existants suffisent : `hooks.py` inchangé)
- Test : `openlab_academy/tests/test_visibilite_frappe.py`, `openlab_academy/tests/test_habillage.py`

**Interfaces :**
- Consomme : `Visibilite`, `Refus`, `redirection` (Tâche 2) ; `phase_lancement()` (Tâche 6) ; `CHAMP_LIMITE` (Tâche 4).
- Produit :
  - `SourceVisibiliteFrappe` (port `SourceVisibilite`) : `fenetre(cours)` = dates de la cohorte publiée la plus
    récente (`start_date` max) qui porte le parcours ; `limite(cours)` = `CHAMP_LIMITE` ; `tous_les_cours()`,
    `cours_limites_publies()`.
  - `lms.refus_pour(utilisateur: str, cours: str | None) -> Refus | None` (Guest compris ; agent = rôle de
    `ROLES_NON_BLOQUES` ; résultat en cache de requête comme `bloque_pour`). Erreur de calcul : journalisée (titre
    « Visibilité des parcours : calcul impossible ») → `FERME` pour un parcours limité, aucun masquage sinon.
  - `class ParcoursFerme(frappe.ValidationError)` et `class ParcoursCache(frappe.ValidationError)`, avec
    `redirection` posée aussi dans `frappe.local.response["redirection"]`, comme `ParcoursBloque`.
  - `_refuser_si_bloque` devient `_refuser(cours, utilisateur=None)` : refus de visibilité d'abord, puis paiement ;
    utilisé par `get_lesson`, `get_course_details`, `get_quiz_with_questions`, `check_answer`,
    `mark_lesson_progress`, `save_progress`, `create_certificate`, `avant_certificat`, `avant_soumission_*`.
  - `lecture_permise` : `False` aussi pour un refus de visibilité (Guest compris) ; `conditions_lecons|quiz|devoirs|
    exercices` excluent `Visibilite.refuses(agent)` en plus des parcours bloqués.
  - `before_request` : page de parcours refusée → 302 vers `redirection(refus, cours)` ; idem pour
    `/lms/batches/<lot>` dont tous les parcours sont cachés → `/lms/courses`.
  - `paiement.js` : `cible()` accepte `ParcoursFerme` (préfixe `/parcours-ferme/`) et `ParcoursCache` (chemin exact
    `/lms/courses`) en plus de `ParcoursBloque`.

- [ ] **Step 1 : tests** — `test_visibilite_frappe.py` (parcours limité et cohorte créés dans le test ; date du site
  remplacée par `mock.patch.object(lms, "aujourd_hui")`) :
  - `test_page_parcours_ferme_redirigee` (apprenant et Guest, `GET` HTML → 302 `/parcours-ferme/<cours>`) ;
    `test_page_parcours_cache_redirigee` (→ `/lms/courses`) ; `test_page_ouverte_servie`.
  - `test_api_lecon_refusee_hors_fenetre` : `get_lesson` → `ParcoursFerme`, `lms_utils.get_lesson` jamais appelé ;
    `frappe.client.get("Course Lesson", …)` → `frappe.PermissionError` ; `frappe.get_list("Course Lesson",
    {"course": …})` vide ; `get_quiz_with_questions` et `check_answer` refusés — pour un apprenant **et** pour Guest.
  - `test_dernier_jour_ouvert_lendemain_ferme` : `aujourd_hui = fin` → servi ; `fin + 1 jour` → `ParcoursFerme`.
  - `test_dates_de_cohorte_changees_a_chaud` : `end_date` repoussée → de nouveau ouvert dans la requête suivante.
  - `test_agents_jamais_refuses` : pour chaque rôle de `ROLES_NON_BLOQUES`, parcours fermé **et** caché → pages,
    `get_lesson`, listes de leçons servies.
  - `test_phase_decochee_tout_revient` : parcours caché refusé, case décochée → servi ; recochée → refusé ; aucune
    écriture en base entre les deux (`modified` du parcours inchangé).
  - `test_inscrit_d_un_parcours_cache_le_voit_cache`.
  - `test_parcours_non_limite_hors_lancement_inchange` et `test_blocage_paiement_inchange` (la suite
    `test_blocage_frappe` reste verte).
  - `test_habillage.py` : `paiement.js` contient `ParcoursFerme`, `/parcours-ferme/`, `ParcoursCache`, et toujours
    aucun `innerHTML`.
- [ ] **Step 2 : lancer** `test_visibilite_frappe` → FAIL.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer** `test_visibilite_frappe`, `test_blocage_frappe`, `test_verrou_frappe`, `test_habillage` → PASS.
- [ ] **Step 5 : commit** `feat(academy): parcours fermé hors de sa fenêtre et parcours cachés pendant le lancement`.

### Tâche 10 : inscriptions refusées et rattachement à la cohorte

**Fichiers :**
- Modifier : `openlab_academy/entrypoints/paiement.py` (`avant_inscription_parcours`, `avant_inscription`),
  `openlab_academy/entrypoints/lms.py` (`refuser_inscription`), `openlab_academy/hooks.py`
  (`doc_events["LMS Enrollment"]["after_insert"]`), `openlab_academy/translations/en.csv`
- Test : `openlab_academy/tests/test_inscription_lancement_frappe.py`

**Interfaces :**
- Consomme : `lms.refus_pour` (Tâche 9) ; cohorte-fenêtre (Tâche 7).
- Produit :
  - `lms.refuser_inscription(membre: str, cours: str) -> None` : `FERME` →
    `frappe.throw(_("Les inscriptions à ce parcours sont fermées."), frappe.ValidationError)` ; `CACHE` →
    `frappe.throw(_("Ce parcours n'est pas disponible pour le moment."), frappe.ValidationError)`. Appelée au début de
    `avant_inscription_parcours` (parcours de l'inscription) et de `avant_inscription` (chaque parcours de la
    cohorte : refus si **tous** sont refusés). Membre agent → jamais refusé.
  - `entrypoints/lancement.py` : `rejoindre_cohorte(doc, method=None) -> None` (`after_insert` de `LMS Enrollment`) :
    parcours limité, membre non agent, inscription pas déjà issue d'une cohorte → crée l'inscription à la
    cohorte-fenêtre (`LMS Batch Enrollment`, `ignore_permissions`) si elle n'existe pas ; sans effet sinon.

- [ ] **Step 1 : tests** — `test_refus_hors_fenetre` (avant `debut` et après `fin` : `LMS Enrollment` et
  `LMS Batch Enrollment` → `frappe.ValidationError` avec le texte exact) ; `test_inscription_ouverte_acceptee` (aucun
  dossier de paiement créé, `disable_self_learning` à 0) ; `test_inscription_directe_rattache_a_la_cohorte` (une seule
  `LMS Batch Enrollment`, aucune boucle, rejouable) ; `test_inscription_parcours_cache_refusee` ;
  `test_agent_inscrit_hors_fenetre` ; `test_phase_decochee_inscription_permise` ; `test_message_en_anglais` (membre
  `en` → « Enrollment for this course is closed. »).
- [ ] **Step 2 : lancer** → FAIL.
- [ ] **Step 3 : implémenter, compléter `en.csv`.**
- [ ] **Step 4 : lancer** ce module, `test_inscription_directe_frappe`, `test_paiement_inscription_frappe`,
  `test_parcours_gratuits_frappe` → PASS.
- [ ] **Step 5 : commit** `feat(academy): inscriptions refusées hors fenêtre ou pendant le lancement`.

### Tâche 11 : catalogue, accueil et recherche filtrés

**Fichiers :**
- Créer : `openlab_academy/entrypoints/catalogue.py`
- Modifier : `openlab_academy/hooks.py` (`override_whitelisted_methods`)
- Test : `openlab_academy/tests/test_catalogue_frappe.py`

**Interfaces :**
- Consomme : `Visibilite.refuses(agent)` via `lms` (Tâche 9).
- Produit — surcharges (chemins à confirmer par `grep -n "def <nom>(" lms/lms/utils.py lms/lms/api.py
  lms/command_palette.py` dans le conteneur), chacune appelant l'original :
  - `lms.lms.utils.get_courses` et `lms.lms.utils.get_course_count` : exclusion par filtre avant l'appel
    (`name not in refusés`), pour garder pagination et total exacts ; si `enrolled`/`created` posent déjà `name`, la
    liste résolue est intersectée sans perdre la portée « à soi » (`is_self_scoped`).
  - `lms.lms.api.get_my_courses`, `lms.lms.utils.get_related_courses` : résultats filtrés.
  - `lms.lms.utils.get_batches`, `lms.lms.api.get_my_batches`, `lms.lms.utils.get_batch_details` : cohorte retirée
    (ou `ParcoursCache`) quand **tous** ses parcours sont refusés.
  - `lms.command_palette.search_sqlite` : lignes `LMS Course` refusées et `LMS Batch` entièrement refusées retirées.
  - Agents : aucun filtre (appel direct de l'original).

- [ ] **Step 1 : tests** — 5 parcours publiés dont 2 cachés (phase active), apprenant puis Guest :
  `test_catalogue_sans_parcours_caches` (`get_courses({})`, onglet `live`) ; `test_pagination_exacte`
  (`limit_page_length=2` → pages de 2 puis 1, `get_course_count` = 3) ; `test_onglet_inscrits_filtre` (inscrit à un
  caché → absent de `{"enrolled": 1}`) ; `test_parcours_de_lancement_en_tete` (featured → premier de `{"live": 1}`) ;
  `test_accueil_filtre` ; `test_recherche_filtree` ; `test_cohortes_filtrees` ; `test_agents_voient_tout` ;
  `test_phase_decochee_catalogue_complet`.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : implémenter.** **Step 4 : lancer** → PASS.
- [ ] **Step 5 : commit** `feat(academy): catalogue, accueil et recherche limités aux parcours visibles`.

### Tâche 12 : retrait quotidien du catalogue après la fin

**Fichiers :**
- Modifier : `openlab_academy/entrypoints/lancement.py`, `openlab_academy/infrastructure/visibilite_frappe.py`,
  `openlab_academy/hooks.py` (`scheduler_events["cron"]["5 0 * * *"]`), `openlab_academy/entrypoints/install.py`
  (`after_migrate` : appel en dernier, après `seed.run` qui republie)
- Test : `openlab_academy/tests/test_retrait_catalogue_frappe.py`

**Interfaces :**
- Consomme : `Visibilite.echus()` (Tâche 2).
- Produit : `SourceVisibiliteFrappe.depublier(cours: str) -> None` (`db_set("published", 0,
  update_modified=False)`) ; `lancement.retirer_parcours_echus(commit: bool = True) -> tuple[str, ...]` (parcours
  retirés ; journalisé). Ni leçon, ni inscription, ni progression, ni certificat touchés.

- [ ] **Step 1 : tests** — `test_parcours_echu_depublie` (`aujourd_hui = fin + 1`) ; `test_dernier_jour_reste_publie` ;
  `test_parcours_non_limite_jamais_depublie` ; `test_progression_et_certificat_conserves` (inscription,
  `LMS Course Progress`, `LMS Certificate` intacts ; certificat toujours listé pour l'apprenant) ;
  `test_republication_puis_retrait` (`after_migrate` d'un parcours échu → toujours `published = 0`) ;
  `test_parcours_echu_absent_du_catalogue` (apprenant : `get_courses({})` ne le contient plus) ;
  `test_tache_planifiee_declaree`.
- [ ] **Step 2 : lancer** → FAIL. **Step 3 : implémenter.** **Step 4 : lancer** → PASS, puis la suite complète
  `bash docker/dev-test.sh` (arrière-plan) → PASS, couverture ≥ 99 %.
- [ ] **Step 5 : commit** `feat(academy): parcours de lancement retiré du catalogue après sa fermeture`.

### Tâche 13 : validation de bout en bout

- [ ] **Step 1 :** banc de dev arrêté ; reconstruire et relancer la pile `ol-academy` (`docker-compose -p ol-academy
  build` puis `up -d`, `bench --site academy.localhost migrate`).
- [ ] **Step 2 :** dans Chrome, en visiteur, apprenant puis administrateur, sur ordinateur et à 375 px : catalogue
  (parcours IA agentique seul et premier, mis en avant à l'accueil), page du parcours, inscription, leçon avec vidéo
  (lien YouTube collé dans `/app/course-lesson/…`) et sans vidéo, quiz, rendu du projet final et correction.
- [ ] **Step 3 :** décocher « Phase de lancement » dans `/app/reglages-openlab-academy` → tous les parcours
  reviennent ; recocher.
- [ ] **Step 4 :** passer les dates de la cohorte dans le passé (console) → page « Parcours fermé », inscription
  refusée, leçon refusée par l'API ; `bench --site academy.localhost execute
  openlab_academy.entrypoints.lancement.retirer_parcours_echus` → parcours absent du catalogue, certificat toujours
  dans le profil ; administrateur : tout reste accessible.
- [ ] **Step 5 :** corriger tout écart par une tâche courte (test d'abord), puis publier sur `develop` (subtree split)
  et vérifier la CI.
