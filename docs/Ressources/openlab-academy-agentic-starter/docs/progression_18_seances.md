# Progression du projet fil rouge — 18 séances et un projet final

Le fil rouge est un agent de recouvrement assisté et contrôlé, construit sur un jeu de douze factures
fictives libellées en francs CFA. Chaque séance ajoute une capacité au même dépôt : rien n'est
recommencé de zéro, et chaque livrable est vérifiable par un test ou par une trace.

| Séance | Apprentissage | Évolution du projet | Livrable vérifiable |
|---|---|---|---|
| 1 — Histoire | Cinq âges de l'agentique, ce qui a échoué et ce qui sert encore | Cadrer la mission et situer les choix dans leur histoire | Trois décisions datées dans `decisions.md` |
| 2 — Les LLM | Jetons, fenêtre de contexte, échantillonnage, entraînement, modèles propriétaires, open weight et open source | Choisir un modèle cible et chiffrer son coût et son contexte | Fiche du modèle retenu et de ses limites |
| 3 — Prompting | Prompt système, descriptions d'outils, techniques qui tiennent à la mesure, frontière donnée/consigne | Écrire le prompt système et les descriptions des six outils | `prompts/agent.md` versionné avec son journal |
| 4 — Anatomie d'un agent | Boucle percevoir, raisonner, agir, observer ; agent, chatbot, RAG, workflow ; degrés d'autonomie | Écrire le domaine, le chargeur de données et le squelette d'agent | `recouvrement/domaine.py` et ses tests, sans aucune clé |
| 5 — Tool calling | Contrats d'arguments, porte unique, liste blanche, erreurs lisibles | Écrire les contrats, les actions et la porte unique | Un outil hors liste blanche refusé et journalisé |
| 6 — Orchestrateur sans framework | Chaînage, routage, parallélisation, réflexion ; les cinq gardes | Écrire la boucle complète et le modèle simulé | Une garde cassée rend exactement un test rouge |
| 7 — Brancher un vrai modèle | Clés, interface de modèle, streaming, modèle local, coût par exécution | Brancher un modèle distant puis local derrière la même interface | Exécution réelle tracée, coût mesuré en F CFA |
| 8 — État et reprise | Trois mémoires, écriture atomique, idempotence, reprise | Rendre l'état durable et la reprise sûre | Coupure en plein vol, reprise sans doublon |
| 9 — Mémoire longue et RAG | Découpage, index lexical, index vectoriel, fusion, citations | Ajouter le sixième outil, la recherche dans la politique interne | Chaque réponse cite le passage utilisé |
| 10 — Chaînes LangChain | Composants et composition, chargeurs, découpeur, récupérateurs, fusion, citations | Refaire la recherche documentaire avec le cadre, à côté de la vôtre | Mêmes citations, prompt envoyé capturé, tableau comparatif chiffré |
| 11 — LangGraph | Graphe d'états, points de sauvegarde, pause humaine | Réécrire la même boucle en graphe | Reprise après interruption, validation en pause |
| 12 — CrewAI, PydanticAI, GenAI | Rôles, sorties typées, SDK au plus près du modèle | Trois écritures de plus, puis le comparatif | Tableau de mesures sur trois exécutions et choix argumenté |
| 13 — MCP | Serveur, client, frontière de confiance, cycle de vie | Publier les outils de lecture, consommer par le client | Un client tiers utilise vos outils |
| 14 — Multi-agents et A2A | Superviseur, contrats d'échange, topologies, trois pannes | Découper le portefeuille en lots et agréger | Surcoût mesuré contre la boucle simple |
| 15 — Sécurité et évaluation | Injection indirecte, propriétés vérifiables, traces, risques résiduels | Écrire les douze critères et le jeu d'évaluation | Douze critères exécutés, cinq éliminatoires verts |
| 16 — Empaqueter et déployer | Interface HTTP, conteneur, secrets, pipeline, retour arrière | Rendre le projet installable et déployable sans vous | Un tiers installe et exécute sans votre aide |
| 17 — Exploiter | Mesures, seuils, plafond de dépense, journal, incidents, dérive | Instrumenter, plafonner, préparer la marche à suivre | Retour arrière déclenché pour de vrai |
| 18 — Système d'information réel | Port unique et adaptateurs, bac à sable, lecture seule, rapprochement des paiements, identité opposable | Brancher Odoo, Dolibarr ou ERPNext derrière un port ; justificatifs Nextcloud, valideur Keycloak, pilotage Metabase, n8n et Grafana | Mêmes tests en mémoire et sur l'ERP réel, sans toucher au domaine |
| Projet final | Intégration, démonstration et revue technique | Exécuter le parcours complet jusqu'à la demande de validation ; l'action finale reste simulée | Dépôt documenté, démonstration de 7 minutes et dossier de preuves |

## Livrable final attendu
1. Dépôt exécutable et documenté, installable depuis zéro par un tiers.
2. Diagramme de composants et diagramme de séquence.
3. Jeu de tests automatisés, dont les douze critères d'acceptation, et leurs résultats.
4. Traces montrant décisions, appels d'outils, résultats, erreurs et validation humaine.
5. Mesures : taux de réussite, nombre d'étapes, appels d'outils invalides, latence et coût en francs CFA.
8. Une ligne de registre par brique externe branchée : apport, protocole, comportement en cas d'indisponibilité.
6. Registre des risques et limites.
7. Démonstration commentée et README d'installation.

## Variante selon le profil
- Vibe codeurs : insister sur le traçage des appels d'outils, le contexte envoyé au modèle, les schémas et les limites de l'autonomie.
- Développeurs : insister sur les ports et adaptateurs, le typage, les tests, l'idempotence, les erreurs et la séparation métier/orchestration.
- Experts IA : insister sur les stratégies de planification, les évaluations, le choix du modèle, les patterns et les compromis multi-agents.

## Règle pédagogique
Chaque séance ajoute une capacité au même produit, et tout le code est écrit dans le cours, fichier par
fichier, avec les tests qui vont avec. La correction complète du projet final n'est publiée qu'après la
date limite de dépôt.
