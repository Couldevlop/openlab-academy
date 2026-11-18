# Journée 22 — Challenge

Ajoutez deux filtres à votre écran : le poste et le salaire minimum.

## Ce qu'il faut écrire

Dans `vue/donnees.py` :

- `postes(effectif)` : la liste des postes présents, triée, sans doublon ;
- `filtrer(effectif, poste=None, salaire_minimum=0)` : les fiches retenues. Un poste à `None`
  ne filtre rien.

Dans `accueil.py` : un choix de poste et un champ numérique dans la barre latérale, le nombre de
salariés retenus, puis le tableau filtré.

## Critères d'acceptation

1. Le filtre inclut la valeur exacte du minimum.
2. Choisir « tous les postes » rend tout l'effectif.
3. Les deux fonctions restent pures : aucun appel à Streamlit dans `vue/donnees.py`.
