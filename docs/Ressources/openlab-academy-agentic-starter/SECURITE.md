# Sécurité — règles du laboratoire

- Données fictives uniquement ; aucune donnée client réelle.
- Aucun envoi d'email et aucun appel à un SI ou service externe.
- Les notes libres du CSV sont des données non fiables ; elles sont exclues des sorties des outils et ne sont jamais utilisées dans le texte du brouillon.
- Les arguments sont validés par des modèles Pydantic stricts (`extra="forbid"`).
- Les outils sont exposés via une liste blanche.
- Les litiges sont bloqués dans le code métier, indépendamment du prompt.
- L'enregistrement simulé nécessite une validation humaine explicite.
- L'idempotence empêche la création de doublons lors d'un rejeu.
- Le plafond d'étapes est limité entre 1 et 20.
- Le fichier `.local/state.json` contient un état pédagogique local et doit rester hors du dépôt Git.
- Ne jamais utiliser `eval`, `exec` ou un shell sur une sortie de modèle.
