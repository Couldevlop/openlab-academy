# Journée 09 — Challenge

Écrivez `anciennete_en_mois(embauche, aujourdhui)` dans `dates.py`.

## Ce qu'il faut écrire

La fonction reçoit deux objets `date` et rend un nombre entier de **mois révolus**. Le mois en
cours ne compte que lorsque le jour d'embauche est atteint.

Une date d'embauche postérieure à la date du jour lève une `ValueError`.

## Critères d'acceptation

1. La fonction rend un entier.
2. La date du jour n'est jamais lue à l'intérieur de la fonction.
3. Les trois cas limites passent : embauche en cours de mois, 29 février, date future.
