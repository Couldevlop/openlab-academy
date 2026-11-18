# Journée 23 — Challenge

Ajoutez trois indicateurs en haut de l'écran, dans `rh/indicateurs.py`.

## Ce qu'il faut écrire

- `effectif_total(effectif)` ;
- `masse_salariale(effectif)` ;
- `salaire_median(effectif)` : 0 sur un effectif vide. La médiane, pas la moyenne : un seul très
  haut salaire ne doit pas déplacer l'indicateur.

Les trois s'affichent avec `st.metric`, sur une ligne de trois colonnes, et suivent les filtres.

## Critères d'acceptation

1. Les indicateurs sont calculés dans `rh/`, jamais dans l'écran.
2. La médiane d'un effectif pair est la demi-somme des deux salaires du milieu.
3. Un effectif vide n'écrase pas l'écran : les trois indicateurs valent 0.
