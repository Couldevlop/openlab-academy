# Journée 18 — Challenge

Ajoutez `POST /salaries`.

## Ce qu'il faut écrire

La route reçoit un `SalarieEntrant`, l'ajoute au dépôt et rend le détail créé avec le code 201.
Un matricule déjà pris rend 409. Un champ inconnu dans le corps est refusé.

## Critères d'acceptation

1. Une création réussie rend 201 et la fiche créée apparaît dans la liste.
2. Un salaire négatif, une date future ou un champ inconnu rendent 422.
3. Le même matricule deux fois rend 409.
