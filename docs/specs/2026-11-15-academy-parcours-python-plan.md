# Bases de Python, jour après jour — plan d'implémentation

> Exécution : une tâche à la fois, test rouge avant le code, un commit par tâche.

**But** : publier un parcours payant de 35 journées qui mène un débutant complet à une application RH
ivoirienne démontrable, en garantissant à chaque journée une preuve exécutable.

**Architecture** : rien de neuf côté plateforme. Chaque journée se publie en deux leçons (un rappel à quiz,
une leçon à challenge) dans un parcours à progression séquentielle ; le cœur métier écrit en Python pur
pendant trois semaines est ensuite exposé par FastAPI, affiché par Streamlit, puis porté sur Django.

**Pile** : fichier de parcours YAML, rendu EditorJS du LMS, figures SVG déterministes, dépôts ZIP
déterministes, pytest côté apprenant.

**Spec** : `docs/specs/2026-11-14-academy-bases-python-design.md`.

## Contraintes globales

- Contenu pédagogique en français, jamais dans `_()` ; textes d'interface dans `_()` + `translations/*.csv`.
- Aucun tiret cadratin d'incise dans la prose (test du dépôt).
- Montants en FCFA, sans décimale, séparateur d'espace insécable fine.
- Données RH entièrement fictives ; le cours dit pourquoi des données réelles ne quittent pas le poste.
- Le cœur métier n'importe ni framework, ni fichier, ni réseau : règle enseignée et vérifiée par les tests
  livrés aux apprenants.
- Aucun secret en clair, y compris dans les exemples ; `.env.exemple` et variables d'environnement.
- Dépôts et carnets déterministes : `--verifier` doit rendre un résultat identique.
- Pas de Docker, pas de service à monter : SQLite pour Django. Le parcours annonce « aucun prérequis ».
- Windows, macOS et Linux donnés en une ligne chacun quand les commandes diffèrent.

## Ce que la plateforme fournit déjà (vérifié dans le code du LMS)

- `LMS Course.enforce_lesson_completion` verrouille les leçons en séquence pour les inscrits
  (`lms/lms/permissions.py:enforces_lesson_completion`, `compute_locked_lessons`).
- Une leçon n'est complète que si **les blocs de son propre contenu** sont satisfaits : quiz réussi au score
  exigé et devoir rendu (`course_lesson.py:get_quiz_progress`, `get_assignment_progress`,
  `apply_enforcement_flags`, exigés par défaut). Une leçon sans quiz est complète sans quiz : c'est ce qui
  permet le couple « rappel à quiz seul » / « leçon à challenge seul ».
- Les réglages d'exercices (délai, tentatives, score) sont propres à chaque parcours depuis le
  commit `65773230`, et une séance peut se passer d'exercices depuis `1cb0f2a6`.

## Points de vigilance (à couvrir par des tests, le plan dit où)

1. **Un délai d'exercices nul doit rester nul.** Le socle livré traite 0 comme « réglage global » ; ce
   parcours exige l'ouverture immédiate. Sans correction, l'apprenant attend une heure (T0.1).
2. **Un rappel ne doit créer ni livrable ni mise en situation**, sinon la leçon du jour reste fermée
   jusqu'à un rendu qui n'existe pas (T0.2).
3. **Une leçon de challenge ne doit pas créer de quiz**, sinon la journée suivante attend un quiz absent
   de la page (T0.2).
4. **Un quiz de rappel épuisé ferme le parcours** : tentatives généreuses, et un formateur peut rouvrir.
   Le texte du rappel doit le dire (T1, T9 recette).
5. **Le harnais de tests livré doit échouer au départ et passer avec la solution de référence** : vérifié
   par un test du dépôt qui exécute les deux, journée par journée (T9).

## Fichiers

| Fichier | Responsabilité |
|---|---|
| `apps/.../data/parcours/07-python-application-rh.yaml` | le parcours : 6 blocs, 69 leçons, capstone |
| `apps/.../data/ressources/depot-python-jNN.zip` | dépôt de départ d'une journée (énoncé, tests rouges, corrigé de la veille) |
| `apps/.../data/ressources/carnet-python-semaine-N.zip` | carnet d'exercices de la semaine |
| `apps/.../data/ressources/python-*.svg`, `python-ouverture-NN.jpg` | figures et photos du parcours |
| `docs/Ressources/openlab-academy-python-rh/` | dépôt source du formateur : solution complète et tests des 35 journées |
| `docs/Ressources/construire_depots_python.py` | construit les 35 dépôts et les 7 carnets depuis le dépôt source, `--verifier` |
| `docs/Ressources/schemas/figures_python.py` | figures SVG du parcours |
| `apps/.../tests/test_parcours_python_rh.py` | invariants du parcours (structure, alternance, challenges, dépôts) |
| `apps/.../tests/test_evaluations_module.py` | pièces d'évaluation choisies par séance (T0.2) |

---

## T0 — Socle : ce qui manque encore

### T0.1 Un parcours peut exiger un délai d'exercices nul

**Fichiers** : `infrastructure/yaml_source.py`, `infrastructure/depot_ouvertures_frappe.py`,
`entrypoints/install.py`, `patches/delai_exercices_non_regle.py`, `tests/test_verrou.py`,
`tests/test_verrou_frappe.py`, `tests/test_yaml_source.py`, `patches.txt`.

- [ ] Test rouge : `parametres: {delai_exercices_minutes: 0}` est accepté et donne `exercices.delai_minutes == 0`
      (remplace `test_delai_nul_refuse_au_profit_du_reglage_global`).
- [ ] Test rouge : `DelaiExercicesFrappe().minutes(lecon)` rend `0` quand le parcours porte 0, et `None`
      quand il porte `-1`.
- [ ] Retirer `_MINIMUMS` de `yaml_source.py` ; la sentinelle « non réglé » devient `-1`.
- [ ] `CHAMP_DELAI` : champ Int de défaut `"-1"`, description « -1 : appliquer le réglage de la plateforme ».
- [ ] Patch `delai_exercices_non_regle` : passe à `-1` les parcours restés à `0` (sites déjà migrés).
- [ ] Tests verts, couverture ≥ 99 %, commit.

### T0.2 Les pièces d'évaluation sont choisies séance par séance

Le rappel veut un quiz seul ; la leçon du jour, un livrable seul. `sans_exercices: true` devient une valeur
parmi quatre.

**Fichiers** : `domain/parcours.py`, `infrastructure/yaml_source.py`, `infrastructure/depot_frappe.py`,
`infrastructure/editorjs.py`, `tests/test_evaluations_module.py`, `tests/test_exercices.py`,
`tests/test_exercices_frappe.py`.

**Interfaces produites** :
- `domain/parcours.py` : `class Evaluations(Enum)` avec `COMPLETES = "completes"` (défaut),
  `QUIZ = "quiz"`, `LIVRABLE = "livrable"`, `AUCUNE = "aucune"` ; `Module.evaluations: Evaluations`.
- Propriétés `Module.veut_quiz` et `Module.veut_livrable`, lues par `depot_frappe` et `editorjs`.

- [ ] Test rouge (domaine) : `evaluations: QUIZ` exige le quiz au complet et refuse mise en situation,
      livrable ou travaux pratiques rendus inutiles ; `LIVRABLE` refuse un quiz ; `AUCUNE` refuse les deux ;
      `COMPLETES` garde les invariants actuels.
- [ ] Test rouge (domaine) : `livrable` facultatif quand `veut_livrable` est faux, toujours exigé sinon.
- [ ] Test rouge (YAML) : clé `evaluations:` avec une valeur hors des quatre refusée en citant les valeurs
      admises ; `sans_exercices` n'existe plus.
- [ ] Test rouge (publication) : une séance `QUIZ` crée un `LMS Quiz` et aucun `LMS Assignment` ; sa leçon
      ne porte ni bloc `assignment`, ni ligne « Format : ~N h », ni titre « Livrable » ; une séance
      `LIVRABLE` crée le devoir seul et aucun quiz.
- [ ] Implémenter, tests verts, commit.

### T0.3 Le fichier de parcours pose la progression séquentielle

**Fichiers** : `domain/parcours.py`, `infrastructure/yaml_source.py`, `infrastructure/depot_frappe.py`,
`tests/test_depot_frappe.py`, `tests/test_yaml_source.py`.

- [ ] Test rouge : `progression_sequentielle: true` dans le YAML écrit `enforce_lesson_completion = 1` sur
      `LMS Course` à la création, à la republication et par `completer`, et `0` sinon.
- [ ] Implémenter dans `_drapeaux`, tests verts, commit.

---

## Gabarit d'une journée (écrit une fois, appliqué 35 fois)

**Leçon de rappel** `num: "NNR"`, titre « JNN · Rappel de la veille », `evaluations: quiz` :
cinq puces reprises de la veille, aucune notion nouvelle, puis le quiz de cinq questions. La première
journée n'a pas de rappel.

**Leçon du jour** `num: "NN"`, titre « JNN · <notion> », `evaluations: livrable` et sept sections, dans
cet ordre :

1. `Ce que vous saurez faire ce soir` — une phrase à l'infinitif, vérifiable.
2. `Le problème d'abord` — une situation du fil rouge encore hors de portée.
3. `La notion` — explication courte, une figure si la notion est spatiale, du code sinon.
4. `À la main` — ce que l'apprenant tape, exécute et observe.
5. `L'astuce du jour` — une habitude de professionnel.
6. `Le piège du jour` — l'erreur fréquente, avec son message exact.
7. `Challenge` — l'épreuve, ses critères d'acceptation, la commande de test, l'archive du jour.

**Dépôt du jour** `depot-python-jNN.zip` : `enonce.md`, le squelette à compléter, `tests/test_jNN.py`
rouge, `corrige/` de la veille, `LISEZ-MOI.md` avec les trois commandes (installer, lancer les tests,
lancer le programme).

---

## Les 35 journées

Colonnes : notion du jour · astuce · piège · challenge (ce que les tests livrés vérifient).

### Semaine 1 — Premiers pas (bloc 01, J01 à J05)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 01 | installer Python, exécuter un fichier, variables, `print` | lire une trace d'erreur de bas en haut | guillemet non fermé, `SyntaxError` | `fiche.py` expose `nom`, `poste`, `salaire_fcfa` et `resume` ; les tests importent le module et vérifient les quatre valeurs |
| 02 | nombres, division, arrondi, f-strings, montants en FCFA | nommer l'unité dans la variable (`salaire_fcfa`) | `0.1 + 0.2`, `/` contre `//` | `salaire_annuel(mensuel, primes)` et `formater_fcfa(montant)` ; tests sur 13 cas dont 0, un montant à 7 chiffres, un arrondi |
| 03 | `if / elif / else`, booléens, comparaisons | nommer la condition dans une variable | `=` contre `==`, casse des chaînes | `droit_aux_conges(mois_anciennete)` selon la règle du cours ; tests aux bornes 0, 11, 12, 13 |
| 04 | `for`, `range`, `while`, accumulation | accumuler, afficher une seule fois à la fin | boucle infinie, compteur faux d'une unité | `masse_salariale(salaires)` et `plus_haut_salaire(salaires)` ; tests sur liste vide, un élément, ex æquo |
| 05 | la première fonction : `def`, paramètres, `return`, docstring | une fonction, un verbe | un calcul qui `print` et rend `None` | regrouper les quatre journées dans `rh/calculs.py` ; les tests refusent tout `print` dans le module (capture de sortie) |

### Semaine 2 — Structures de données (bloc 02, J06 à J10)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 06 | listes : indexer, trancher, ajouter, trier | `sorted()` quand on veut une copie | index hors bornes, `sort()` qui rend `None` | `effectif_trie(noms)` et `trois_derniers(noms)` ; tests sur accents et liste vide |
| 07 | dictionnaires : clés, `.get`, parcours | clés stables, en minuscules sans accent | `KeyError` sur une clé absente | `salarie(nom, poste, date_embauche, salaire_fcfa)` et `lire_champ(salarie, champ, defaut)` |
| 08 | listes de dictionnaires, filtres, compréhensions | compréhension sur une ligne, boucle sinon | copie superficielle, mutation partagée | `par_poste(effectif)`, `filtrer_par_salaire(effectif, mini)` ; un test prouve que l'effectif d'origine n'a pas bougé |
| 09 | dates : `datetime.date`, ancienneté, mois incomplet | tout en ISO `AAAA-MM-JJ` | soustraire deux dates donne des jours | `anciennete_en_mois(embauche, aujourdhui)` ; tests sur embauche en cours de mois, 29 février, date future refusée |
| 10 | chaînes : normaliser, découper, joindre, aligner | normaliser à l'entrée, une fois | espaces et casse invisibles dans un nom | état « effectif par poste » aligné, rendu en chaîne par `etat_par_poste(effectif)` ; test sur la chaîne exacte |

### Semaine 3 — Fonctions, modules, tests, validation (bloc 03, J11 à J15)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 11 | modules et paquets, `import`, `if __name__ == "__main__"` | un module, un sujet | exécuter au lieu d'importer, import circulaire | ranger le code en `rh/calculs.py`, `rh/etats.py`, `main.py` ; les tests importent chaque module isolément |
| 12 | fichiers et CSV : `with`, UTF-8, `csv.DictReader` | `with` toujours, chemin construit, jamais concaténé | accents cassés par l'encodage, chemin relatif | `charger_effectif(chemin)` dans `rh/fichiers.py` ; les tests vérifient que `rh/calculs.py` n'importe ni `csv` ni `pathlib` |
| 13 | erreurs : `try / except`, erreur métier, message utile | échouer tôt, dire quoi faire | `except:` nu qui avale tout | `DonneeInvalide` levée par le chargement ; tests sur fichier absent, colonne manquante, salaire illisible |
| 14 | se tester : pytest, cas limites, rouge puis vert | un test, une phrase en nom | tester l'implémentation, test sans assertion | l'apprenant écrit lui-même trois tests manquants sur les congés ; le harnais vérifie qu'ils échouent sur une implémentation fautive fournie |
| 15 | valider aux frontières avec Pydantic | un modèle d'entrée distinct du modèle métier | valider partout au lieu de l'entrée | `SalarieEntrant` refuse salaire négatif, date future, poste vide ; le cœur reste sans validation ; état des trois rapports au vert |

### Semaine 4 — FastAPI (bloc 04, J16 à J20)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 16 | HTTP en vingt minutes, `uvicorn`, `GET /sante`, docs auto | lire `/docs` avant d'écrire un client | port déjà pris, rechargement qui masque une erreur | `GET /sante` rend `{"etat": "ok"}` ; test avec `TestClient` |
| 17 | exposer le cœur sans le modifier ; le mot « hexagonal » | le cœur ne connaît pas FastAPI | logique métier recopiée dans la route | `GET /salaries`, `GET /salaries/{matricule}` avec 404 propre ; un test vérifie que `rh/` n'importe pas `fastapi` |
| 18 | écrire : `POST /salaries`, 201, 422 de Pydantic | réutiliser le modèle d'entrée de J15 | valider deux fois, message d'erreur maison inutile | création refusée sur salaire négatif avec 422 et champ fautif nommé |
| 19 | paramètres de requête, erreurs métier vers codes HTTP | une erreur métier, un code, un message | tout en 500, ou un 200 qui cache un échec | `GET /etats/masse-salariale?mois=AAAA-MM` ; tests sur mois invalide (422) et mois sans données (200 et total nul) |
| 20 | tester l'API, secrets hors du code (`pydantic-settings`, `.env`) | `.env.exemple` suivi, `.env` jamais | clé d'API écrite dans le code | suite d'API verte et test qui refuse tout secret en dur dans le dépôt |

### Semaine 5 — Streamlit (bloc 05, J21 à J25)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 21 | premier écran, widgets, exécution descendante du script | l'écran appelle le cœur, il ne calcule pas | tout recalculer à chaque clic | écran qui affiche les trois chiffres de la direction ; tests sur les fonctions de préparation, pas sur l'affichage |
| 22 | tableaux et filtres (poste, ancienneté) | filtrer dans une fonction testable | filtre appliqué à l'affichage seulement | `effectif_filtre(effectif, poste, anciennete_min)` ; tests sur filtres cumulés et résultat vide |
| 23 | formulaire d'embauche branché sur le cœur | message d'erreur lisible par un humain | données perdues au rechargement | l'ajout refusé affiche la raison ; test sur la fonction qui traduit l'erreur métier en message |
| 24 | graphiques : masse salariale par poste, absences du mois | une mesure par axe, jamais deux échelles | camembert à douze parts illisible | `serie_masse_par_poste(effectif)` rend des couples triés ; test sur l'ordre et les totaux |
| 25 | cache (`st.cache_data`), mise en forme, scénario de démonstration | préparer la démo en deux minutes chronométrées | cache qui garde des données périmées | `demo.md` : le scénario, et l'écran complet ; le harnais vérifie que les trois pages se chargent sans exception |

### Semaines 6 et 7 — Django (bloc 06, J26 à J35)

| J | Notion | Astuce | Piège | Challenge et tests |
|---|---|---|---|---|
| 26 | pourquoi un autre modèle ; `startproject`, SQLite, `runserver` | lire l'arborescence avant d'écrire | lancer sans migrations initiales | projet qui démarre, `manage.py check` sans avertissement |
| 27 | modèles et migrations : `Salarie`, `Poste`, `Absence` | une migration par intention | modifier la base à la main | les trois modèles et leurs contraintes ; tests de modèle sur l'unicité du matricule |
| 28 | l'ORM : créer, filtrer, agréger (`aggregate`, `annotate`) | laisser l'ORM écrire le SQL | donnée du client interpolée dans une requête brute | `masse_salariale_par_poste()` en une requête ; un test refuse tout `raw(` ou `%` dans les requêtes |
| 29 | l'admin : back-office de l'effectif | déclarer les colonnes et les filtres utiles | tout exposer, y compris le salaire, à tout le monde | admin utilisable ; test qui vérifie l'enregistrement des trois modèles |
| 30 | vues et gabarits (MVT) : liste et fiche | une vue, une responsabilité | logique métier dans le gabarit | deux pages ; tests de vue sur le code de réponse et le contexte |
| 31 | formulaires Django, validation côté serveur | valider au serveur, l'écran n'est qu'un confort | se fier à la validation du navigateur | formulaire d'embauche ; test d'un POST invalide qui ne crée rien |
| 32 | authentification : `login`, `logout`, `login_required` | un utilisateur de démonstration, jamais en production | page sensible laissée ouverte | pages protégées ; test d'accès anonyme redirigé |
| 33 | rôles et permissions : groupes RH et manager | les droits se vérifient au serveur | masquer un bouton et croire la page protégée | un manager ne voit pas les salaires ; test par rôle sur chaque page |
| 34 | commande de gestion qui importe le CSV via le cœur de la semaine 3 | le cœur survit au troisième habillage | recoder les règles dans Django | `manage.py importer_effectif fichier.csv` ; test qui compare le résultat à celui du cœur Python pur |
| 35 | finir et montrer : états, `TestCase`, `check --deploy`, `DEBUG=False` | relire la liste de contrôle avant de montrer | `DEBUG=True` et clé secrète versionnée | application complète, suite verte, `check --deploy` sans alerte critique |

**Capstone** (chapitre final) : « Votre application RH, montrée à quelqu'un » : le dépôt, le fichier
`demo.md`, la suite de tests verte et une démonstration de cinq minutes.

---

## T1 — Le fichier de parcours et son annonce

**Fichiers** : `data/parcours/07-python-application-rh.yaml`, `tests/test_parcours_python_rh.py`,
`data/ressources/python-couverture.jpg`, `docs/Ressources/CREDITS-ILLUSTRATIONS.md`.

- [ ] Test rouge `test_parcours_python_rh.py` : le fichier charge, porte 6 blocs, 69 leçons, alternance
      rappel puis leçon pour J02 à J35, J01 sans rappel, un capstone, `projets_par_portfolio: 0`,
      `delai_exercices_minutes: 0`, `tentatives_max: 10`, `score_min: 80`,
      `progression_sequentielle: true`, `gratuit: false`, et un dépôt cité par chaque leçon du jour.
- [ ] Écrire le squelette du fichier : fiche du parcours, les 6 blocs, les 69 modules réduits à leur
      titre et leur `evaluations`, le capstone.
- [ ] Couverture du catalogue : photographie libre créditée, recadrée en 1200 × 630.
- [ ] Tests verts, commit.

## T2 à T7 — Rédaction, une semaine par tâche

Un commit par semaine. Pour chacune (T2 = semaine 1, … T7 = semaines 6 et 7, dix journées) :

- [ ] Les cinq rappels : cinq puces, aucune notion nouvelle, quiz de cinq questions dont les distracteurs
      sont des erreurs plausibles, explications écrites.
- [ ] Les cinq leçons : les sept sections du gabarit, l'astuce et le piège du tableau, le code en blocs
      `code` avec le langage, les tableaux de décision là où ils aident.
- [ ] Les figures de la semaine dans `figures_python.py`, rendues en SVG, citées avec leur légende.
- [ ] Les challenges : énoncé, critères d'acceptation, commande de test.
- [ ] Vérifier : `python -m compileall` sur les extraits exportés, test de typographie, test du parcours,
      couverture ≥ 99 %.
- [ ] Commit.

## T8 — Dépôt source, dépôts du jour et carnets

**Fichiers** : `docs/Ressources/openlab-academy-python-rh/`, `docs/Ressources/construire_depots_python.py`,
`data/ressources/depot-python-jNN.zip`, `data/ressources/carnet-python-semaine-N.zip`.

- [ ] Test rouge : pour chaque journée, le harnais du dépôt de départ **échoue**, et il **passe** sur la
      solution de référence du dépôt source. Le test exécute pytest dans un dossier temporaire.
- [ ] Dépôt source du formateur : la solution complète des 35 journées, chacune avec ses tests.
- [ ] `construire_depots_python.py` : dérive les 35 dépôts de départ (solution retirée, tests conservés,
      corrigé de la veille inclus) et les 7 carnets, horodatage figé, ordre des entrées stable,
      `--verifier` qui échoue si une archive a bougé.
- [ ] Vérifier le déterminisme en deux constructions successives, puis commit.

## T9 — Recette et sécurité

- [ ] Publier le parcours sur le banc de développement, s'inscrire comme apprenant d'essai.
- [ ] Parcourir J01 à J03 : le rappel verrouille la leçon, le quiz réussi l'ouvre, le challenge rendu ouvre
      le lendemain, et les exercices sont accessibles immédiatement (délai nul).
- [ ] Vérifier qu'un quiz épuisé se rouvre par le formateur, et que le texte du rappel l'annonce.
- [ ] Télécharger un dépôt du jour hors inscription : refus ; inscrit : archive servie.
- [ ] Affichage 375 px sur la leçon la plus chargée.
- [ ] Audit de sécurité complet (compétence `security-audit`) sur les lots T0, puis publication.
