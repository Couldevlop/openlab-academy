# Journée 17 — Challenge

Décrivez ce que l'API montre, dans `api/sorties.py`, et ajoutez la route de détail.

## Ce qu'il faut écrire

- `SalarieResume` : matricule, nom, poste. **Pas le salaire** : une liste consultée par tout le
  monde n'a pas à diffuser les rémunérations.
- `SalarieDetail` : les cinq champs.
- `GET /salaries/{matricule}` : le détail, ou 404 avec un message clair.

## Critères d'acceptation

1. La liste ne contient aucun salaire, même si le dépôt en a un.
2. Le détail d'un matricule inconnu rend 404, jamais 500.
3. Les modèles de sortie sont déclarés sur les routes.
