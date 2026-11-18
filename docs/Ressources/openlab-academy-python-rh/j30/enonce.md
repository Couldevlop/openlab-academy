# Journée 30 — Challenge

Livrez deux pages : la liste des salariés et la fiche d'un salarié.

## Ce qu'il faut écrire

- `liste_salaries` : la liste, le poste chargé avec elle, et l'état par poste dans le contexte ;
- `fiche_salarie(requete, matricule)` : la fiche, ou **404** si le matricule n'existe pas.

Les gabarits sont fournis.

## Critères d'acceptation

1. Les deux pages répondent 200 et passent par leur gabarit.
2. Un matricule inconnu rend 404.
3. Afficher dix salariés ne coûte pas dix requêtes de plus.
