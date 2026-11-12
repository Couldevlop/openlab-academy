# TP séance 7 — Sécurité, évaluation et traces

## Objectif
Faire passer l'intégralité du jeu d'acceptation, prouver qu'une instruction malveillante cachée dans une donnée
reste une donnée, et sortir une trace exploitable de chaque exécution.

## Prérequis
- Séances 2 à 4 intégrées ; `pytest -q` vert avant d'ouvrir la séance.
- Avoir lu `SECURITE.md` et `tests/criteres_acceptation.csv`.

## Déroulé indicatif — 3 heures
1. 0–25 min : injection de prompt directe et indirecte. Lecture de la colonne `note_non_fiable` du CSV, et de la
   note hostile portée par `FAC-006`.
2. 25–50 min : les trois défenses du socle, dans le code : la note est retirée de la sortie de l'outil, le texte du
   brouillon n'incorpore aucune note libre, le litige est bloqué en dur.
3. 50–75 min : moindre privilège et liste blanche. `blocked_tool` — pourquoi un outil inconnu est **journalisé**
   et pas seulement refusé.
4. 75–85 min : pause.
5. 85–120 min : exécution commentée des douze critères AC-01 à AC-12. Chaque apprenant exécute, lit la sortie et
   note la criticité.
6. 120–150 min : observabilité. Produire une trace par exécution : étape, outil, arguments, résultat, durée ;
   et ce qu'il est interdit d'écrire dans une trace.
7. 150–172 min : registre des risques résiduels. Trois risques minimum, avec leur mesure d'atténuation et ce qui
   reste accepté.
8. 172–180 min : quiz de sortie.

## Défi apprenant
1. Ajouter un cas d'évaluation qui échouerait si la note de `FAC-006` influençait le brouillon.
2. Ajouter un cas qui échouerait si un outil hors liste blanche s'exécutait sans être journalisé.
3. Produire la trace d'une exécution complète, lisible par un tiers, sans donnée sensible.
4. Rédiger le registre des risques résiduels du projet.

## Indices graduels
- *Indice 1* : pour prouver qu'une note n'influence rien, comparer le brouillon produit avec et sans la note dans
  le CSV de test — le texte doit être identique.
- *Indice 2* : un test de journalisation lit `snapshot()["blocked_tools"]`, pas la sortie console.
- *Indice 3* : une trace qui contient un identifiant de validation est acceptable ; une trace qui contient le texte
  intégral du brouillon ne l'est pas en production.

## Livrables
- rapport de tests des douze critères d'acceptation, avec leur criticité ;
- deux nouveaux cas d'évaluation verts ;
- trace d'une exécution complète ;
- registre des risques résiduels.

## Contrôle de fin de séance
Aucun critère bloquant en échec. Un seul critère bloquant rouge interdit le passage à la séance 8.
