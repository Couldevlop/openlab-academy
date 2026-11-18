# Journée 27 — Challenge

Écrivez les modèles `Poste`, `Salarie` et `Absence`, puis créez la migration.

## Ce qu'il faut écrire

- `Poste` : un libellé unique.
- `Salarie` : matricule **unique**, nom, poste (clé étrangère protégée), date d'embauche,
  salaire entier positif.
- `Absence` : salarié, début, fin, motif facultatif, et une contrainte en base qui refuse une fin
  antérieure au début.

Puis : `python manage.py makemigrations effectif`.

## Critères d'acceptation

1. Deux salariés ne peuvent pas porter le même matricule.
2. Une absence qui finit avant de commencer est refusée par la base, pas seulement par le code.
3. `makemigrations --check` ne réclame aucune migration manquante.
