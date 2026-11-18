# Journée 28 — Challenge

Écrivez `effectif/requetes.py`.

## Ce qu'il faut écrire

- `masse_salariale_par_poste()` : `{libellé: {"effectif": n, "masse_fcfa": m}}`, calculé par la
  base **en une seule requête**, trié par libellé ;
- `salaries_du_poste(libelle)` : les salariés d'un poste, avec leur poste déjà chargé.

## Critères d'acceptation

1. L'agrégat ne coûte qu'une requête, quel que soit le nombre de salariés.
2. Lire les salariés d'un poste puis afficher leur poste ne déclenche aucune requête de plus.
3. Aucune requête brute, aucune valeur de filtre collée dans du SQL.
