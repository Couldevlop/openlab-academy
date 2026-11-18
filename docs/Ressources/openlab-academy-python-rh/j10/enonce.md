# Journée 10 — Challenge

Écrivez `etat_par_poste(effectif)` dans `etats.py`.

## Ce qu'il faut écrire

La fonction rend une **chaîne** de plusieurs lignes : une ligne d'en-tête, puis une ligne par
poste, dans l'ordre alphabétique, avec le nombre de salariés et la masse salariale.

Chaque ligne est alignée : le poste sur douze caractères à gauche, l'effectif sur quatre à droite,
la masse sur douze à droite.

```
Poste       Nb      Masse
RH           2     670000
```

Les noms des postes sont normalisés avant regroupement : espaces écrasés, casse de titre.

## Critères d'acceptation

1. La fonction rend une chaîne et n'affiche rien.
2. Les postes apparaissent dans l'ordre alphabétique.
3. Deux écritures du même poste comptent pour un seul poste.
