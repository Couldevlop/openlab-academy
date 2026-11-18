# Journée 25 — Challenge

Terminez l'écran de la semaine : mettez le chargement en cache, et montrez-le à quelqu'un.

## Ce qu'il faut écrire

- `vue/chargement.py` : `charger_effectif()`, décorée par `st.cache_data`, seul endroit où les
  données entrent dans l'écran ;
- `accueil.py` : l'écran complet, qui appelle ce chargement une fois.

## Critères d'acceptation

1. Le chargement est le seul endroit de l'écran qui connaisse la source des données.
2. L'écran n'importe plus directement l'effectif d'exemple.
3. Le cœur et la préparation des données restent sans Streamlit.
