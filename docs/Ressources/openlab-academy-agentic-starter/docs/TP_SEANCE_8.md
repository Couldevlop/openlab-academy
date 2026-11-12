# TP séance 8 — Capstone : démonstration et revue d'architecture

## Objectif
Assembler et défendre le projet. L'apprenant exécute le parcours complet jusqu'à la demande de validation —
l'action finale reste simulée — présente une démonstration de sept minutes et remet son dossier de preuves.

## Prérequis
- Séances 1 à 7 intégrées, `pytest -q` vert, aucun critère bloquant en échec.
- Dossier de preuves préparé **avant** la séance : le temps de séance sert à démontrer, pas à rédiger.

## Déroulé indicatif — 3 heures
1. 0–15 min : rappel du barème (`docs/grille_jury.md`), des cinq conditions éliminatoires et du format de passage.
2. 15–35 min : dernière vérification d'environnement, en salle : installation à blanc depuis l'archive de la première leçon, tests,
   démonstration. Un dépôt qui ne s'installe pas ne peut pas être évalué.
3. 35–140 min : passages. Sept minutes de démonstration et huit minutes de questions par apprenant ou binôme.
4. 140–150 min : pause.
5. 150–172 min : revue d'architecture collective. Les trois défauts les plus fréquents observés, et leur
   correction.
6. 172–180 min : clôture, suites possibles — notamment le branchement d'un modèle local.

## Déroulé imposé de la démonstration — 7 minutes
1. 0–1 min : le cas métier et la décision agent / workflow, en une phrase chacune.
2. 1–2 min : le diagramme de composants, à l'écran.
3. 2–4 min : exécution réelle. Recherche, exposition, brouillon, demande de validation, approbation par un humain
   nommé, enregistrement simulé.
4. 4–5 min : une tentative bloquée, au choix : facture en litige, outil hors liste blanche, ou enregistrement sans
   approbation.
5. 5–6 min : la trace et une mesure.
6. 6–7 min : un risque résiduel assumé et ce qu'il faudrait pour aller en production.

## Dossier de preuves attendu
1. Dépôt exécutable et documenté (installation depuis zéro, en une page).
2. Diagramme de composants et diagramme de séquence.
3. Jeu de tests automatisés et leurs résultats.
4. Traces montrant décisions, appels d'outils, résultats, erreurs et validation humaine.
5. Mesures : taux de réussite des scénarios, nombre d'étapes, appels d'outils invalides, latence, et coût si un
   modèle est utilisé.
6. Registre des risques et des limites.
7. Démonstration commentée et `README` d'installation.

## Évaluation
Barème sur 100 de `docs/grille_jury.md`, seuil pédagogique interne de 70/100, et réussite obligatoire des cinq
contrôles éliminatoires :

- une facture en litige ne peut pas être relancée ;
- aucune action simulée enregistrée sans validation humaine ;
- aucun contenu libre ne remplace une règle métier ;
- aucun appel d'outil non autorisé ne s'exécute ;
- aucun envoi réel n'est déclenché.

Ce seuil est une règle interne de formation ; il ne constitue ni une certification ni une reconnaissance
officielle.

## Contrôle de fin de séance
Un seul contrôle éliminatoire en échec invalide le projet, quel que soit le total obtenu au barème.
