# Journée 15 — Challenge

Écrivez `SalarieEntrant` dans `rh/entrees.py` et branchez-le sur le chargement.

## Ce qu'il faut refuser

- un salaire négatif ;
- une date d'embauche dans le futur ;
- un poste vide.

Chaque refus devient une `DonneeInvalide` qui nomme la ligne et le champ fautif.

## Critères d'acceptation

1. La validation n'existe qu'au chargement.
2. `rh/calculs.py` ne contient aucun contrôle de type ni de borne.
3. Les tests des journées 11 à 14 passent toujours.
