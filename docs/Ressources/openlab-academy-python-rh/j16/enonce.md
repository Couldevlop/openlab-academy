# Journée 16 — Challenge

Écrivez `api/main.py` : une application FastAPI avec deux routes de lecture.

## Ce qu'il faut écrire

- `GET /sante` rend `{"etat": "ok"}` ;
- `GET /salaries` rend la liste des fiches du dépôt, triée par matricule.

Le dépôt se construit une seule fois, à partir de `rh.exemple.FICHES`.

## Critères d'acceptation

1. L'application s'appelle `app`.
2. Les deux routes répondent 200.
3. Le cœur `rh/` n'importe pas FastAPI.
