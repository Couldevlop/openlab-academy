# TP séance 4 — État, reprise et validation humaine

## Objectif
Faire survivre un agent à une interruption. L'apprenant démontre qu'un processus coupé entre la demande de
validation et l'enregistrement reprend sans créer de doublon, et que l'approbation reste un geste humain.

## Prérequis
- Socle vert ; `.local/state.json` supprimé pour partir d'un état propre.
- Avoir lu la section « Démonstration de validation humaine » du `README.md`.

## Déroulé indicatif — 3 heures
1. 0–20 min : mémoire de travail, état partagé, checkpoint. Ce qui doit être persisté et ce qui ne doit jamais
   l'être.
2. 20–50 min : lecture de `workflow.py` — `_load_state`, `_save_state` (écriture par fichier temporaire puis
   remplacement), `events`, `idempotency`.
3. 50–70 min : le parcours complet à la main, dans un shell Python : `prepare_draft`, `submit_for_approval`,
   `approve`, `record_simulated_reminder`. Observer `.local/state.json` après chaque appel.
4. 70–80 min : pause.
5. 80–110 min : couper le processus juste après `submit_for_approval`. Recréer un `LocalWorkflow` sur le même
   fichier d'état, constater que la demande en attente est retrouvée et non dupliquée.
6. 110–140 min : idempotence. Rejouer `record_simulated_reminder` avec la même clé, puis avec la même clé sur un
   autre brouillon. Expliquer les deux réponses.
7. 140–165 min : l'humain dans la boucle. Pourquoi `approve()` n'est pas dans le registre des outils, et ce qui se
   passerait s'il y était.
8. 165–180 min : quiz de sortie.

## Défi apprenant
1. Écrire un test qui démontre AC-11 : interruption après la demande de validation, puis reprise sans doublon.
2. Écrire un test qui démontre AC-08 : rejeu de la même clé d'idempotence, aucun second enregistrement.
3. Écrire un test qui démontre AC-06 : enregistrement refusé sans approbation.
4. Ajouter un compteur de reprises dans le journal d'événements, sans casser les tests existants.

## Indices graduels
- *Indice 1* : la reprise se simule en instanciant un second `LocalWorkflow` sur le même `state_path` ; aucun
  processus à tuer réellement.
- *Indice 2* : `submit_for_approval` réutilise une demande déjà `pending` — c'est là que se joue l'absence de
  doublon.
- *Indice 3* : une clé d'idempotence réutilisée pour un **autre** brouillon doit échouer, pas renvoyer l'existant.

## Livrables
- démonstration interruption/reprise, rejouable par une commande ;
- trois tests d'acceptation verts (AC-06, AC-08, AC-11) ;
- extrait du journal d'événements commenté.

## Contrôle de fin de séance
Un `pytest -q` après deux exécutions consécutives de la démonstration donne le même nombre d'enregistrements.
