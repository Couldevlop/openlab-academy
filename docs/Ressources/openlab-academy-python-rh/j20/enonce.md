# Journée 20 — Challenge

Terminez l'API de la semaine : ajoutez `GET /etats/par-poste`, qui rend pour chaque poste le
nombre de salariés et la masse salariale.

Le calcul appartient au cœur : la route ne fait que l'appeler.

## Critères d'acceptation

1. L'état est calculé par `rh/calculs.py`, pas par la route.
2. Les postes sont rendus dans l'ordre alphabétique.
3. Le cœur n'importe toujours ni FastAPI ni Pydantic.
