# Journée 26 — Challenge

Livrez un projet Django qui démarre, déclare l'application `effectif`, et ne laisse rien de
secret dans le code.

## Trois choses à corriger dans `config/settings.py`

1. l'application `effectif` n'est pas déclarée ;
2. la clé secrète est écrite en dur : elle doit venir de l'environnement, avec une valeur de
   développement par défaut ;
3. le mode debug est allumé quoi qu'il arrive : il doit venir de l'environnement et valoir faux
   par défaut.

## Critères d'acceptation

1. `python manage.py check` ne signale rien.
2. `effectif` figure dans les applications installées.
3. Aucune clé de production dans le dépôt, et `DEBUG` faux par défaut.
