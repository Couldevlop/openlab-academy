# Journée 21 — Challenge

Écrivez votre premier écran : `accueil.py`, et la préparation des données dans
`vue/donnees.py`.

## Ce qu'il faut écrire

- `colonnes_affichees(effectif)` : rend la liste des lignes à afficher, avec les colonnes
  `matricule`, `nom` et `poste`, dans cet ordre. **Pas le salaire** : un écran ouvert dans un
  bureau de passage n'affiche pas les rémunérations.
- `accueil.py` : un titre, une légende qui dit que les données sont fictives, et le tableau.

## Lancer l'écran

`python -m streamlit run accueil.py`

Les tests livrés n'ont pas besoin de Streamlit : ils éprouvent la préparation des données et la
forme de l'écran.

## Critères d'acceptation

1. `colonnes_affichees` rend exactement trois colonnes, dans l'ordre.
2. L'écran appelle la préparation des données, il ne la refait pas.
3. Aucun calcul dans `accueil.py`.
