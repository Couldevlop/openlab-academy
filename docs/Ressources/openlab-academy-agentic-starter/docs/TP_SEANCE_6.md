# TP séance 6 — Multi-agent : ce que la délégation coûte vraiment

## Objectif
Mesurer, plutôt que supposer, le gain d'une architecture multi-agents. L'apprenant compare un agent unique à un
orchestrateur accompagné de deux analystes spécialisés, sur des segments de factures indépendants.

## Prérequis
- Séance 3 intégrée (fonction de routage par segment).
- Séance 5 facultative pour cette séance : le multi-agent se joue ici en local, sans MCP.

## Déroulé indicatif — 3 heures
1. 0–20 min : décomposition d'une tâche, délégation, contexte partagé. Les trois façons de perdre de l'argent en
   multi-agent : contexte recopié, allers-retours inutiles, conclusions contradictoires.
2. 20–45 min : conception. Un orchestrateur qui segmente, deux analystes — « retards récents » et « retards
   lourds » — un agrégateur qui réconcilie.
3. 45–75 min : implémentation des deux analystes comme fonctions bornées, avec leur propre plafond d'étapes.
4. 75–85 min : pause.
5. 85–120 min : implémentation de l'orchestrateur et de l'agrégation ; traitement des segments en parallèle, puis
   total unique d'exposition.
6. 120–150 min : instrumentation. Pour les deux architectures : nombre d'étapes, nombre d'appels d'outils, durée
   de bout en bout, taille du contexte transmis.
7. 150–172 min : rédaction du rapport comparatif qualité / coût / latence et discussion de la cohérence (que fait-on
   si les deux analystes classent la même facture différemment ?).
8. 172–180 min : quiz de sortie.

## Défi apprenant
1. Orchestrateur + deux analystes, segments strictement disjoints (une facture traitée une seule fois).
2. Test d'invariant : la somme des expositions des segments égale l'exposition de l'agent unique.
3. Mesures des deux architectures dans un tableau reproductible.
4. Rapport comparatif d'une page, avec une recommandation explicite pour ce cas métier.

## Indices graduels
- *Indice 1* : des segments disjoints se prouvent par un test d'ensemble, pas par relecture.
- *Indice 2* : la latence d'un traitement local est dominée par la lecture du CSV ; mesurer les appels d'outils
  autant que les secondes.
- *Indice 3* : il est parfaitement admis de conclure que le multi-agent ne se justifie pas ici, si les mesures le
  disent.

## Livrables
- deux architectures exécutables dans le même dépôt ;
- test d'invariant sur les segments ;
- rapport comparatif qualité / coût / latence avec recommandation.

## Contrôle de fin de séance
La recommandation s'appuie sur le tableau de mesures du dépôt, et l'invariant d'exposition est vert.
