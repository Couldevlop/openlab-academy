# Journée 29 — Challenge

Rendez l'administration utilisable par l'équipe RH.

## Ce qu'il faut écrire

Les trois modèles enregistrés, avec pour les salariés : les colonnes matricule, nom, poste et
date d'embauche, un filtre par poste, une recherche sur matricule et nom, et le poste chargé avec
la liste.

## Ce qu'il ne faut surtout pas faire

Créer un compte dans une migration. Un compte né d'une migration a un mot de passe écrit dans le
dépôt, le même sur toutes les installations : c'est une porte ouverte, pas une commodité. Les
comptes se créent avec `createsuperuser`.

## Critères d'acceptation

1. Les trois modèles apparaissent dans l'administration.
2. La liste des salariés affiche les quatre colonnes et ne multiplie pas les requêtes.
3. Après migrations, la base ne contient aucun compte.
