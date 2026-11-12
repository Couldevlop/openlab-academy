# TP séance 3 — Orchestration : workflow fixe ou agent

## Objectif
Choisir un pattern d'orchestration sur preuve, et non par habitude. L'apprenant implémente deux fois le même
traitement — une fois en workflow fixé par le code, une fois en boucle d'agent — puis justifie son choix par écrit.

## Prérequis
- Socle vert, défi de la séance 2 intégré (`montant_min_eur` et ses tests).

## Déroulé indicatif — 3 heures
1. 0–20 min : les cinq patterns de base — chaînage, routage, parallélisation, orchestrateur-exécutants,
   évaluateur-optimiseur. Un exemple métier par pattern.
2. 20–40 min : les deux styles d'agent, ReAct (raisonner et agir pas à pas) et plan-and-execute (planifier puis
   exécuter). Ce que chacun coûte en étapes.
3. 40–70 min : implémentation A — un workflow fixe. Une fonction qui enchaîne recherche, routage par segment,
   calcul d'exposition, sans aucune liberté de décision.
4. 70–80 min : pause.
5. 80–115 min : implémentation B — le même traitement par un plan passé à `run_agent`, avec plafond d'étapes.
6. 115–145 min : routage des factures par segment : âge du retard, statut de litige, montant. Trois chemins, trois
   traitements.
7. 145–170 min : mesure et comparaison — nombre d'étapes, nombre d'appels d'outils, déterminisme du résultat sur
   trois exécutions.
8. 170–180 min : quiz de sortie.

## Défi apprenant
1. Écrire la fonction de routage : `segment(facture) -> "rappel_simple" | "escalade" | "exclu"`, litiges exclus.
2. Produire les deux implémentations sur le même jeu de 12 factures fictives.
3. Vérifier par un test que les deux donnent la même exposition totale.
4. Rédiger une note de décision d'une demi-page : quel pattern pour ce cas, et à partir de quand l'agent devient
   justifié.

## Indices graduels
- *Indice 1* : le routage est une règle métier, donc testable sans modèle ni agent.
- *Indice 2* : `run_agent` accepte un `plan` ; un workflow fixe n'est qu'un plan que personne ne peut modifier.
- *Indice 3* : si les deux implémentations donnent le même résultat pour un coût moindre, c'est le workflow qui
  gagne — la bonne réponse de cette séance peut être « pas d'agent ici ».

## Livrables
- deux implémentations comparées, dans le même dépôt ;
- test d'équivalence du total d'exposition ;
- note de décision signée (pattern retenu, seuil de bascule, risque accepté).

## Contrôle de fin de séance
La note de décision cite au moins une mesure chiffrée issue du dépôt. Un choix justifié par « c'est plus moderne »
est refusé.
