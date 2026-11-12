# Supports des 8 séances et alignement du fil rouge « recouvrement » — plan de réalisation

> **Pour l'exécutant :** suivre ce plan tâche par tâche. Étapes en cases à cocher (`- [ ]`).

**Sources :** `docs/Ressources/Compte_rendu_OpenLab_Academy_Operationnel_03.docx` (compte rendu opérationnel n° 3,
11 novembre 2026) et `docs/Ressources/openlab-academy-agentic-starter/` (socle Python v0.2.0 : `README.md`,
`docs/progression_8_seances.md`, `docs/brief_apprenant.md`, `docs/grille_jury.md`, `TP_SEANCE_2.md`).

**But :** produire les « supports essentiels des huit séances » annoncés comme à produire par le compte rendu n° 3, et
aligner le parcours publié `06-ia-agentique.yaml` sur le fil rouge réellement exécutable du socle — un agent de
recouvrement assisté et contrôlé sur des factures fictives — à la place du fil rouge « analyse documentaire » rédigé
avant la livraison du socle.

**Décisions prises par le porteur du projet (12 novembre 2026) :**

1. Aligner le parcours 06 sur le socle (un seul fil rouge, celui du dépôt), structure 7 modules + capstone conservée.
2. Produire les supports **à la fois** côté formateur (`TP_SEANCE_n.md` du dépôt) et côté apprenant (leçons du LMS).
3. Corriger les écarts `ruff` du socle.

**Pile :** socle = Python 3.11–3.13, Pydantic 2, pytest. Plateforme = Frappe v15 + LMS, Python 3.11.

## Correspondance des 8 séances et des modules publiés

| Séance (socle) | Module publié | Écart à traiter |
|---|---|---|
| 1 — Comprendre | 01 Anatomie d'un agent IA | livrable + mise en situation à passer au recouvrement |
| 2 — Boucle Python | 02 Tool calling et boucle d'agent | idem + rattacher le socle (`agent.py`, `tools.py`, `contracts.py`) |
| 3 — Orchestration | 03 Patterns d'orchestration | idem ; comparer workflow fixe et agent sur le routage des factures |
| 4 — État et reprise | 04 État, mémoire et reprise sur erreur | idem ; démonstration interruption/reprise et idempotence du socle |
| 5 — MCP et A2A | 05 MCP et interopérabilité | idem ; exposer les outils de lecture et de brouillon en MCP |
| 6 — Multi-agent | 06 Architectures multi-agents et A2A | idem ; orchestrateur + deux analystes sur segments indépendants |
| 7 — Sécurité et qualité | 07 Sécurité, évaluation et observabilité | idem ; note malveillante du CSV et jeu d'acceptation AC-01 à AC-12 |
| 8 — Capstone | `capstone:` | contexte, critères et livrables à passer au recouvrement ; grille /100 |

La structure du parcours ne change donc pas : **7 modules × 3 h + capstone 3 h = 24 h**, quiz de 5 questions,
`projets_par_portfolio: 0`.

## Contraintes globales

- Ne modifier ni `apps/frappe` ni `apps/lms`.
- Architecture hexagonale : `domain/` n'importe jamais `frappe`. Sécurité OWASP au premier plan.
- TDD : un test qui échoue avant chaque ajout de code (`superpowers:test-driven-development`).
- Textes d'interface dans `_()` avec leur entrée dans `openlab_academy/translations/en.csv` ; contenu pédagogique
  (YAML, supports) en français, jamais dans `_()`.
- Tests de la plateforme : `bash docker/dev-test.sh`, **un seul banc à la fois** (RAM du poste très juste).
- Règles non négociables du socle à préserver dans toute reformulation : litige jamais relancé, validation humaine
  explicite avant enregistrement, idempotence, notes libres non instructionnelles, liste blanche d'outils, plafond
  d'étapes, aucun envoi réel.

## Tâches

### T1 — Validation du socle sur le poste (critère de sortie du compte rendu n° 3)

- [x] `py -3.12 -m venv .venv`, `pip install -e ".[dev]"` : réussis.
- [x] `pytest -q` → **16 passed** sous Python 3.12.6 (comble l'écart « 3.11 et 3.12 non testés » du compte rendu).
- [x] `python -m agentic_lab` → 5 factures éligibles, exposition 7 730,00 EUR, aucune relance.
- [x] `ruff check .` → 8 écarts corrigés automatiquement (tri des imports, `collections.abc.Callable`,
      `datetime.UTC`) et `BLE001` de la frontière d'outil documenté par un `noqa` commenté. **All checks passed.**
- [x] Journaliser ces résultats dans `docs/Ressources/openlab-academy-agentic-starter/docs/RAPPORT_VALIDATION_TECHNIQUE.md`
      (section « Validation sur poste formateur, 12 novembre 2026 »).

### T2 — Champ `travaux_pratiques` du module (plateforme)

Les supports de séance doivent être visibles par l'apprenant dans le LMS ; le modèle de module n'a aujourd'hui que
`contenu`, `livrable`, `quiz` et `mise_en_situation`.

- [x] Test rouge `domain/` : un `Module` accepte `travaux_pratiques` facultatif, vide par défaut.
- [x] Test rouge `infrastructure/yaml_source.py` : la clé facultative `travaux_pratiques:` est lue.
- [x] Test rouge `infrastructure/editorjs.py` : `lecon_module` insère une section « Travaux pratiques » après le
      livrable quand le champ est rempli, et n'insère rien quand il est vide.
- [x] Implémenter les trois, vert, sans régression des tests de publication existants.

### T3 — Supports formateur des 8 séances (dépôt socle)

- [x] Renommer `TP_SEANCE_2.md` en `docs/TP_SEANCE_2.md` et aligner son format sur les sept autres.
- [x] Rédiger `docs/TP_SEANCE_1.md` à `docs/TP_SEANCE_8.md` sur le modèle existant : objectif, déroulé minuté sur
      3 h, défi apprenant, livrables vérifiables, indices graduels (la règle pédagogique du socle interdit de donner
      la correction complète au début).
- [x] Séance 8 : déroulé de la démonstration de 7 minutes et du dossier de preuves, adossé à `docs/grille_jury.md`.
- [x] Index `docs/SUPPORTS.md` : table des huit séances, prérequis matériel, état de l'environnement attendu à
      l'entrée de chaque séance.

### T4 — Fil rouge du parcours publié (modules 01 à 07)

- [x] Réécrire les sept `livrable:` en étapes du socle (étape n = capacité ajoutée au même dépôt).
- [x] Réécrire les sept `mise_en_situation:` sur le cas du recouvrement, en gardant une mise en situation ancrée en
      Côte d'Ivoire quand c'est naturel.
- [x] Reprendre `description:` : fil rouge, dépôt fourni, prérequis Python 3.11–3.13, mention explicite « données
      fictives, aucun envoi réel, aucun SI connecté ».
- [x] Remplir `travaux_pratiques:` de chaque module depuis le support de séance correspondant (T3).
- [x] Relire les 35 questions de quiz : conserver celles qui restent justes, réécrire celles qui s'appuient sur le
      fil rouge documentaire.

### T5 — Capstone = séance 8

- [x] `contexte`, `objectifs`, `fonctionnalites`, `stack`, `criteres_acceptation`, `livrables` passés au recouvrement.
- [x] Conditions éliminatoires de `docs/grille_jury.md` portées en `exigences_specifiques` (litige relancé, action
      enregistrée sans validation, contenu libre qui remplace les règles, outil non autorisé exécuté, envoi réel).
- [x] `livrables` = dépôt documenté, diagrammes, jeu de tests et résultats, traces, mesures, registre des risques,
      démonstration de 7 minutes.

### T6 — Vérification

- [x] Tests ciblés hors Docker : `test_domaine`, `test_yaml_source`, `test_editorjs`,
      `test_parcours_ia_agentique` — 70 verts.
- [ ] `bash docker/dev-test.sh` : suite complète verte, couverture maintenue. **Bloqué le 12/11 :** le banc dev
      a dû être reconstruit (le conteneur `frappe` de `poc/docker-compose.yml` ne monte aucun volume pour
      `frappe-bench` : recréer le conteneur détruit le bench, les apps et le site). `poc/init.sh` épingle
      désormais l'interpréteur sur Python 3.12.15, l'image proposant par défaut un Python 3.14 que Frappe v15 ne
      prend pas en charge.
- [ ] Publication du parcours sur le banc de démonstration, puis recette Chrome : leçon d'un module (section
      travaux pratiques présente, quiz, mise en situation), page du capstone, grille de correction.
- [ ] Vérifier l'affichage 375 px (point resté ouvert de la session précédente).
- [ ] Commits en français, un par tâche.

### T7 — Distribution du socle aux apprenants (décidée le 12 novembre 2026)

Le socle est distribué en **archive téléchargeable depuis la leçon**, et non par un dépôt Git : un dépôt imposerait
un compte et la maîtrise de `clone` dès la séance 2, au-delà des prérequis annoncés ; un dépôt public exposerait le
matériel hors cohorte et un dépôt privé obligerait à inviter chaque inscrit. L'archive est un artefact produit à
partir du socle versionné, et l'apprenant démarre son propre dépôt, dont la grille évalue l'historique.

Le porteur du projet a retenu un **téléchargement contrôlé** : l'archive ne doit pas être servie en ressource
publique de l'application.

- [ ] Test rouge : un visiteur, et un utilisateur non inscrit, ne peuvent pas télécharger l'archive.
- [ ] Test rouge : un inscrit ne peut pas la télécharger hors de la fenêtre de sa cohorte (refus `FERME`).
- [ ] Test rouge : un inscrit la télécharge pendant la fenêtre ; rôles non bloqués servis sans condition.
- [ ] Point d'entrée de téléchargement appuyé sur `application/visibilite.py` et les rôles non bloqués de
      `entrypoints/lms.py`, nom de fichier jamais construit depuis une entrée du client (OWASP A01, A03).
- [ ] Lien dans la leçon de la séance 2 et mention de la version de l'archive.
- [ ] Remplacer dans les supports « l'archive fournie par le formateur » par le chemin réel de téléchargement.

## Hors périmètre, à décider par le porteur du projet
- **Adaptateur de modèle local** (interface `ModelClient` + adaptateur Ollama), désigné prochaine étape technique
  prioritaire par le compte rendu n° 3 : hors de ce plan, à traiter après les supports.
- **Gratuité : décidée, pas en attente.** Ce parcours est gratuit (clé `gratuit: true`, aucun tarif, aucun
  échéancier, aucun blocage pour paiement) ; la question tarifaire du compte rendu n° 3 ne le concerne pas. Restent
  à fixer les dates précises des huit séances et la capacité maximale de la cohorte.
