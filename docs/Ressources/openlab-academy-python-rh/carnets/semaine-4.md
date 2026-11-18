# Carnet de la semaine 4 — Une API autour du cœur

Exercices non notés. Lancez l'API avec `python -m uvicorn api.main:app --reload`, puis ouvrez
`http://127.0.0.1:8000/docs`. Données fictives.

## Jour 16 — première route

1. Ajoutez une route qui rend la date du jour.
2. Appelez une route inexistante et lisez le code renvoyé.
3. Regardez la page `/docs` et retrouvez-y vos deux routes.

## Jour 17 — ce que l'API montre

1. Ajoutez un champ au dépôt sans le déclarer en sortie, et vérifiez qu'il ne sort pas.
2. Demandez un matricule inconnu et lisez le corps de la réponse.
3. Ouvrez `/openapi.json` et retrouvez vos modèles.

## Jour 18 — recevoir

1. Envoyez une création avec un champ en trop, puis sans ce champ.
2. Envoyez un salaire négatif et lisez le détail du refus.
3. Créez deux fois le même matricule.

## Jour 19 — codes et messages

1. Provoquez une panne volontaire et vérifiez que la réponse ne dit rien d'utile à un attaquant.
2. Comparez un 400, un 404 et un 422 sur votre propre API.
3. Cherchez dans votre code un message d'erreur qui cite un chemin de fichier.

## Jour 20 — l'ensemble

1. Ajoutez un salarié, puis rappelez l'état par poste.
2. Déplacez un calcul de la route vers le cœur, et constatez que les tests passent toujours.
3. Comptez les lignes de `api/main.py` : une route qui dépasse dix lignes en fait trop.
