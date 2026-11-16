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
  ou dans un environnement qui en dispose.

Règles tenues par le dépôt source :

1. Le squelette d'une journée fait échouer ses tests ; la solution les fait passer.
2. Les données sont entièrement fictives, et les montants sont en francs CFA sans décimale.
3. Aucun secret, aucune adresse réelle, aucun appel réseau.
