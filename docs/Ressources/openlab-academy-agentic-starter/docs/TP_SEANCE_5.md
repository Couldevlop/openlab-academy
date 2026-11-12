# TP séance 5 — MCP et interopérabilité, A2A décrit

## Objectif
Exposer les outils de lecture et de brouillon du projet derrière un serveur MCP local, et les consommer depuis un
client — sans jamais déplacer les règles métier hors du code. La délégation A2A est décrite, pas branchée.

## Prérequis
- Socle vert, tests d'état et de reprise de la séance 4 verts.
- SDK MCP installé dans l'environnement virtuel de l'apprenant (`pip install "mcp[cli]"`), hors dépendances du
  socle : cette séance ajoute une couche, elle ne modifie pas le cœur.

## Déroulé indicatif — 3 heures
1. 0–25 min : le modèle hôte / client / serveur. Ce qu'un serveur MCP expose : `tools`, `resources`, `prompts`.
   Pourquoi un outil MCP reste une frontière de sécurité, pas un simple appel de fonction.
2. 25–55 min : écrire un serveur MCP local qui expose deux outils seulement :
   `lister_factures_impayees` et `preparer_brouillon_relance`.
3. 55–70 min : vérifier la découverte des outils par un client (l'inspecteur du SDK suffit).
4. 70–80 min : pause.
5. 80–115 min : brancher la boucle du socle sur le serveur : l'agent appelle désormais l'outil *à travers* MCP, et
   le résultat reste identique (5 factures, 7 730,00 EUR).
6. 115–145 min : moindre privilège. Ne jamais exposer `enregistrer_relance_simulee` ni `approve` ; démontrer qu'un
   client MCP ne peut donc pas déclencher l'action finale.
7. 145–170 min : A2A sur le papier. Rédiger la fiche d'Agent Card d'un « agent conformité » à qui l'on
   déléguerait l'examen d'une facture en litige : identité, compétences annoncées, entrées, sorties, limites.
8. 170–180 min : quiz de sortie.

## Défi apprenant
1. Serveur MCP local démarrable par une commande documentée dans le `README` de l'apprenant.
2. Preuve de découverte : capture ou sortie texte listant les deux outils et leurs schémas.
3. Un test qui vérifie qu'un troisième outil n'est pas exposé.
4. Fiche d'Agent Card A2A, une page, avec au moins une limite explicite (« ne décide jamais d'un abandon de
   créance »).

## Indices graduels
- *Indice 1* : les schémas MCP peuvent être dérivés des contrats Pydantic existants ; ne pas les réécrire à la
  main.
- *Indice 2* : la liste blanche du socle (`tools.py`) reste la référence ; le serveur MCP expose un
  sous-ensemble, jamais un sur-ensemble.
- *Indice 3* : si l'on peut enregistrer une relance depuis le client MCP, le moindre privilège est raté — relire
  quels outils sont enregistrés.

## Livrables
- serveur MCP local et sa commande de démarrage ;
- preuve de découverte et d'appel d'au moins un outil ;
- test de non-exposition de l'outil d'écriture ;
- fiche d'Agent Card A2A illustrative.

## Contrôle de fin de séance
Le résultat métier passé par MCP est strictement identique à celui obtenu en appel direct ; sinon, une règle a
fui hors du code.
