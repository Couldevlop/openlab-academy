# Supports des huit séances — index formateur

Supports essentiels du parcours « IA agentique », 8 séances de 3 h, 24 h au total. Chaque séance ajoute une
capacité au **même** dépôt : le projet fil rouge n'est jamais recommencé.

| Séance | Support | Thème | Livrable vérifiable |
|---|---|---|---|
| 1 | [TP_SEANCE_1.md](TP_SEANCE_1.md) | Comprendre : agent, chatbot, RAG ou workflow | Schéma d'architecture + règles métier |
| 2 | [TP_SEANCE_2.md](TP_SEANCE_2.md) | Boucle Python et appels d'outils | Agent sans framework + 4 tests minimum |
| 3 | [TP_SEANCE_3.md](TP_SEANCE_3.md) | Orchestration : workflow fixe ou agent | Deux implémentations + note de décision |
| 4 | [TP_SEANCE_4.md](TP_SEANCE_4.md) | État, reprise et validation humaine | Interruption/reprise + tests d'idempotence |
| 5 | [TP_SEANCE_5.md](TP_SEANCE_5.md) | MCP et interopérabilité, A2A décrit | Serveur MCP local + Agent Card |
| 6 | [TP_SEANCE_6.md](TP_SEANCE_6.md) | Multi-agent et coût de la délégation | Rapport qualité / coût / latence |
| 7 | [TP_SEANCE_7.md](TP_SEANCE_7.md) | Sécurité, évaluation et traces | Rapport de tests, traces, risques résiduels |
| 8 | [TP_SEANCE_8.md](TP_SEANCE_8.md) | Capstone, démonstration et revue | Dossier de preuves + démonstration 7 min |

Documents de cadrage associés : [progression_16_seances.md](progression_16_seances.md),
[brief_apprenant.md](brief_apprenant.md), [grille_jury.md](grille_jury.md),
[INTEGRATION_FIL_ROUGE.md](INTEGRATION_FIL_ROUGE.md), [RAPPORT_VALIDATION_TECHNIQUE.md](RAPPORT_VALIDATION_TECHNIQUE.md).

## Prérequis matériel et logiciel

- Un poste par apprenant, droits d'installation locale, 8 Go de mémoire au minimum.
- L'archive du socle est distribuée par la plateforme : elle est jointe en fichier privé à la première leçon du
  parcours et n'est téléchargeable que par un inscrit, pendant la fenêtre de sa cohorte. Les supports de séance de
  ce dossier, eux, ne sont pas distribués aux apprenants.
- Python 3.11, 3.12 ou 3.13 ; 3.12 et 3.13 sont vérifiés, 3.11 est la borne basse déclarée du socle.
- Terminal, éditeur de code, navigateur récent, connexion internet stable.
- Aucun compte chez un fournisseur de modèle n'est nécessaire pour les séances 1 à 8 : la boucle du socle est
  déterministe.

## État attendu du dépôt à l'entrée de chaque séance

| Entrée en séance | État exigé |
|---|---|
| 1 | Archive téléchargée depuis la première leçon et décompressée, rien d'installé |
| 2 | Cadrage de la séance 1 rendu |
| 3 | `pytest -q` vert, filtre `montant_min_eur` et ses tests |
| 4 | Fonction de routage par segment et test d'équivalence |
| 5 | Tests d'état, de reprise et d'idempotence verts |
| 6 | Routage disponible ; serveur MCP non requis |
| 7 | Séances 2 à 4 intégrées, suite verte |
| 8 | Douze critères d'acceptation passés, dossier de preuves rédigé |

## Règle pédagogique commune

Ne pas donner la correction complète au début d'une séance : fournir les contrats, les critères d'acceptation, puis
les indices graduels du support, dans l'ordre. Un apprenant bloqué plus de quinze minutes reçoit l'indice suivant,
jamais le code.

## Variantes selon le profil de la cohorte

- **Vibe coders** : insister sur le traçage des appels d'outils, le contexte envoyé au modèle, les schémas et les
  limites de l'autonomie.
- **Développeurs** : insister sur les ports et adaptateurs, le typage, les tests, l'idempotence, les erreurs et la
  séparation métier / orchestration.
- **Experts IA** : insister sur les stratégies de planification, les évaluations, le choix du modèle, les patterns
  et les compromis multi-agent.

## Limites à annoncer en séance 1

Le socle ne branche aucun modèle de langage : les décisions de la boucle sont simulées, pour isoler la mécanique.
Les séances 5 et 6 ajoutent MCP et la délégation par-dessus cette boucle. Le branchement d'un modèle local reste
une évolution ultérieure, postérieure à ce programme.
