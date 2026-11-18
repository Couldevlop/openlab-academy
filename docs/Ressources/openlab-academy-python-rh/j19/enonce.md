# Journée 19 — Challenge

Faites parler votre API en codes HTTP, et ne laissez jamais fuir une trace technique.

## Ce qu'il faut écrire

- un gestionnaire qui traduit `DonneeInvalide` en **400** avec son message métier ;
- un gestionnaire de dernier recours qui journalise la panne et rend **500** avec un message
  neutre, sans nom de fichier, sans ligne, sans trace ;
- `GET /salaries/{matricule}/conges` : l'ancienneté en mois et le droit aux congés.

## Critères d'acceptation

1. Une fiche inexploitable rend 400 et nomme ce qui est illisible.
2. Une panne interne rend 500 et ne révèle aucun détail technique.
3. Un matricule inconnu rend toujours 404.
