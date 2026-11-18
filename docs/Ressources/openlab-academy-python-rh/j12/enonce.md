# Journée 12 — Challenge

Écrivez `charger_effectif(chemin)` dans `rh/fichiers.py`.

## Ce qu'il faut écrire

La fonction ouvre le fichier avec `with` et l'encodage `utf-8`, lit les lignes avec
`csv.DictReader`, et rend une liste de fiches. Le salaire est converti en entier.

## Critères d'acceptation

1. Le chemin est reçu en paramètre, jamais écrit en dur.
2. Les accents sont intacts après lecture.
3. `rh/calculs.py` n'importe ni `csv` ni `pathlib`.
