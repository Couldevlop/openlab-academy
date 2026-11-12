# Progression du projet fil rouge — 8 séances

| Séance | Apprentissage | Évolution du projet | Livrable vérifiable |
|---|---|---|---|
| 1 — Comprendre | Agent vs chatbot, RAG et workflow ; anatomie, autonomie, boucle percevoir–raisonner–agir–observer | Cadrer la mission, dessiner le flux, classer les actions par risque | Schéma d'architecture initial + règles métier |
| 2 — Boucle Python | Appels d'outils, JSON/schema, validation, erreurs, liste blanche, plafond d'étapes | Charger les factures fictives, créer les outils de recherche et de calcul, tester les refus | Agent sans framework + 4 tests minimum |
| 3 — Orchestration | Chaîne, routage, parallèle, orchestrateur–exécutants, évaluateur–optimiseur | Comparer workflow fixe et agent ; router les factures selon âge, litige et montant | Deux implémentations comparées + note de décision |
| 4 — État et reprise | Mémoire, état partagé, checkpoint, reprise, idempotence, HITL | Sauvegarder une demande de validation, reprendre après interruption et éviter les doublons | Démonstration interruption/reprise + tests d'idempotence |
| 5 — MCP et A2A | Hôte/client/serveur MCP, tools/resources/prompts ; A2A pour déléguer une tâche à un autre agent | Exposer les outils de lecture et de brouillon via un serveur MCP local ; décrire une délégation A2A | Serveur MCP local + fiche d'Agent Card A2A illustrative |
| 6 — Multi-agent | Décomposition, délégation, contexte partagé, coûts et cohérence | Comparer un agent unique à un orchestrateur et deux analystes spécialisés sur des segments indépendants | Rapport comparatif qualité/coût/latence |
| 7 — Sécurité et qualité | Prompt injection, moindre privilège, évaluation, traces, coût, latence, robustesse | Exécuter le jeu d'acceptation, tester la note malveillante, journaliser chaque étape | Rapport de tests, traces et risques résiduels |
| 8 — Capstone | Intégration, démonstration et revue d'architecture | Exécuter le parcours complet jusqu'à la demande de validation ; l'action finale reste simulée | Dépôt documenté, démonstration de 7 minutes et dossier de preuves |

## Livrable final attendu
1. Dépôt exécutable et documenté.
2. Diagramme de composants et diagramme de séquence.
3. Jeu de tests automatisés et résultats.
4. Traces montrant décisions, appels d'outils, résultats, erreurs et validation humaine.
5. Mesures : taux de réussite des scénarios, nombre d'étapes, appels d'outils invalides, latence et coût si un modèle est utilisé.
6. Registre des risques et limites.
7. Démonstration commentée et README d'installation.

## Variante selon le profil
- Vibe coders : insister sur le traçage des appels d'outils, le contexte envoyé au modèle, les schémas et les limites de l'autonomie.
- Développeurs : insister sur les ports/adaptateurs, typage, tests, idempotence, erreurs et séparation métier/orchestration.
- Experts IA : insister sur les stratégies de planification, les évaluations, le choix du modèle, les patterns et les compromis multi-agent.

## Règle pédagogique
Chaque séance ajoute une capacité au même produit. Ne pas donner la correction complète au début : fournir les contrats, les critères d'acceptation et des indices graduels.
