# Journée 33 — Challenge

Cachez les rémunérations au manager, pour de vrai.

## La règle

L'équipe RH et les superutilisateurs voient les salaires. Les autres comptes connectés voient
l'effectif, les noms et les postes, jamais les montants.

## Ce qu'il faut écrire

- `effectif/roles.py` : `voit_les_salaires(utilisateur)` ;
- les deux vues : le salaire **absent de la réponse** quand le droit manque, pas seulement caché
  par le gabarit. Une donnée envoyée puis masquée reste lisible dans le code source de la page.

## Critères d'acceptation

1. La fiche vue par un manager ne contient aucun montant, nulle part dans la réponse.
2. La fiche vue par l'équipe RH contient le montant.
3. L'état par poste n'est calculé que pour qui a le droit de le voir.
