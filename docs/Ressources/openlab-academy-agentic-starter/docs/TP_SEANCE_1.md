# TP séance 1 — Comprendre : agent, chatbot, RAG ou workflow

## Objectif
Savoir décider si un besoin métier appelle un agent, et cadrer la mission avant d'écrire une ligne de code. À la
fin de la séance, chaque apprenant a posé par écrit le périmètre de son agent de recouvrement, sa boucle et la
classification de ses actions par risque.

## Prérequis
- Poste avec Python 3.11, 3.12 ou 3.13 et un terminal.
- Archive du socle fournie par le formateur, décompressée, **non encore installée** (l'installation est l'objet de
  la séance 2).
- Avoir lu `docs/brief_apprenant.md`.

## Déroulé indicatif — 3 heures
1. 0–15 min : accueil, règles du laboratoire (`SECURITE.md`), ce que la formation ne fera jamais — aucun envoi
   réel, aucun SI connecté, aucune donnée personnelle.
2. 15–45 min : quatre familles de systèmes, sur le même besoin métier. Chatbot : une réponse par message.
   RAG : recherche puis génération, un seul passage. Workflow : étapes fixées par le code. Agent : le modèle
   choisit l'étape suivante dans une boucle.
3. 45–70 min : anatomie d'un agent — modèle, outils, mémoire, contrôle. La boucle percevoir, raisonner, agir,
   observer, et ce qui la termine (réponse sans appel d'outil, plafond d'étapes, budget).
4. 70–80 min : pause.
5. 80–110 min : degrés d'autonomie. Classer sept actions du cas métier de « l'agent propose, l'humain décide » à
   « l'agent agit seul », et dire où se place la frontière acceptable.
6. 110–150 min : atelier de cadrage, par binômes. Mission, sources de données, actions autorisées, actions
   interdites, critères de réussite, conditions d'arrêt.
7. 150–175 min : restitution croisée. Chaque binôme attaque le cadrage d'un autre binôme : quelle action
   irréversible reste possible ?
8. 175–180 min : quiz de sortie.

## Défi apprenant
1. Dessiner le flux de l'agent de recouvrement : entrées, outils, décisions, sorties, point de validation humaine.
2. Écrire les règles métier sous forme de phrases vérifiables (une règle = un test possible).
3. Classer les cinq actions du projet par risque, et justifier laquelle ne doit **jamais** être automatique.
4. Nommer un cas où un simple workflow suffirait et rendrait l'agent inutile.

## Indices graduels
- *Indice 1* : une action est irréversible si son annulation demande un geste humain hors du système.
- *Indice 2* : « exclure les litiges » n'est pas une consigne au modèle, c'est une règle de code.
- *Indice 3* : relire la liste des cinq outils du socle ; l'un d'eux écrit, les autres lisent ou préparent.

## Livrables
- Schéma d'architecture initial (une page, outil libre, photo acceptée).
- Liste des règles métier vérifiables.
- Tableau des actions classées par risque, avec la frontière d'autonomie marquée.

## Contrôle de fin de séance
Le cadrage est accepté si, à la lecture seule du schéma, un tiers peut dire quelle action exige une validation
humaine et pourquoi une facture en litige ne peut pas être relancée.
