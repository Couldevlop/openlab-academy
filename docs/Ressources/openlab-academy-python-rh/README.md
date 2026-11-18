# Dépôt source du parcours « Bases de Python, jour après jour »

Ce dossier n'est pas distribué aux apprenants. Il contient, journée par journée, de quoi fabriquer
le dépôt du jour :

```
jNN/
  enonce.md     le challenge du soir, ses critères d'acceptation
  depart/       le squelette livré à l'apprenant, volontairement incomplet
  solution/     la solution de référence, qui sert aussi de corrigé le lendemain
  tests/        les tests livrés avec le dépôt, rouges au départ
carnets/
  semaine-N.md  les exercices non notés de la semaine, joints au dépôt de son premier jour
```

Les archives se construisent avec `docs/Ressources/construire_depots_python.py` et se déposent dans
les ressources de l'application. Trois usages :

- sans option : écrit les archives et le fichier d'empreintes `data/depots-python.json` ;
- `--verifier` : échoue si une archive livrée diffère de ce que le dépôt source produit ;
- `--eprouver` : lance les tests de chaque journée sur `depart/` puis sur `solution/`, et exige le
  rouge puis le vert. Il demande pytest, absent de l'image de l'application : il se lance à la main
  ou dans un environnement qui en dispose. Deux options l'accompagnent :
  `--python <chemin>` choisit l'interpréteur qui exécute les tests, ce qui permet de garder Django
  dans un environnement dédié plutôt que dans l'environnement principal, et `--journees j26,j27`
  limite la vérification à quelques journées.

Ce que chaque semaine demande pour être éprouvée : rien d'autre que pytest pour les semaines 1 à 3,
pytest plus FastAPI et httpx pour la semaine 4, pytest seul pour la semaine 5 (les tests de l'écran
éprouvent des fonctions pures et la forme du fichier, jamais Streamlit lui-même), pytest plus
Django pour les semaines 6 et 7.

Règles tenues par le dépôt source :

1. Le squelette d'une journée fait échouer ses tests ; la solution les fait passer.
2. Les données sont entièrement fictives, et les montants sont en francs CFA sans décimale.
3. Aucun secret, aucune adresse réelle, aucun appel réseau.
