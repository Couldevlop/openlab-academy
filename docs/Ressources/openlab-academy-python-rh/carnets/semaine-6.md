# Carnet de la semaine 6 — Django, la structure

Exercices non notés. Les commandes se lancent dans le dossier du jour, après
`python -m pip install django`. Données fictives.

## Jour 26 — le projet

1. Lancez `python manage.py check`, puis cassez un réglage et relancez.
2. Lancez `python manage.py runserver` et ouvrez la page d'accueil.
3. Cherchez dans les réglages tout ce qui ne devrait pas être écrit dans le dépôt.

## Jour 27 — modèles

1. Ajoutez un champ, créez la migration, lisez-la avant de l'appliquer.
2. Essayez de créer deux salariés avec le même matricule depuis le shell.
3. Lancez `python manage.py sqlmigrate effectif 0001` et lisez le SQL produit.

## Jour 28 — l'ORM

1. Comptez les requêtes d'une boucle qui lit un poste par salarié.
2. Refaites la même chose avec `select_related` et comparez.
3. Affichez le SQL d'un agrégat avec `print(requete.query)`.

## Jour 29 — administration

1. Créez un compte avec `createsuperuser`, puis connectez-vous.
2. Ajoutez une colonne à la liste des salariés.
3. Cherchez un salarié par son matricule, puis par son nom.

## Jour 30 — vues et gabarits

1. Ajoutez un lien de la fiche vers la liste.
2. Demandez un matricule inconnu et lisez la page renvoyée.
3. Retirez `select_related` et comptez les requêtes de la liste.
