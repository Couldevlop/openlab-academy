# Journée 07 — Challenge

Écrivez `salarie(...)` et `lire_champ(...)` dans `fiches.py`.

## Ce qu'il faut écrire

- `salarie(nom, poste, date_embauche, salaire_fcfa)` : rend un dictionnaire avec exactement les
  clés `nom`, `poste`, `date_embauche` et `salaire_fcfa`.
- `lire_champ(salarie, champ, defaut)` : rend la valeur du champ, ou `defaut` s'il est absent.

## Critères d'acceptation

1. Les clés sont exactement celles demandées, en minuscules et sans accent.
2. `lire_champ` ne lève jamais `KeyError`.
3. `lire_champ` ne modifie jamais la fiche reçue.
