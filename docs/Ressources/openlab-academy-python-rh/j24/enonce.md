# Journée 24 — Challenge

Ajoutez un graphique lisible, préparé dans `vue/graphiques.py`.

## Ce qu'il faut écrire

- `serie_masse_par_poste(effectif)` : `{poste: masse}`, dans l'ordre alphabétique, calculé par le
  cœur ;
- `libelle_axe(montant_maximum)` : `FCFA`, `milliers de FCFA` ou `millions de FCFA`, selon la
  plus grande barre, pour que l'axe reste lisible ;
- dans l'écran : le titre du graphique, le graphique, et un message clair quand le filtre ne
  retient personne.

## Critères d'acceptation

1. Les deux fonctions sont pures et testées sans écran.
2. Un effectif filtré vide affiche un message, pas un graphique vide.
3. Les seuils de l'axe sont ceux de l'énoncé, bornes comprises.
