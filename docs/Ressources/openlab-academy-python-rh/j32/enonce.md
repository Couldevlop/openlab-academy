# Journée 32 — Challenge

Protégez les trois pages de l'effectif : personne d'anonyme n'y entre.

## Ce qu'il faut écrire

Exigez une session ouverte sur `liste_salaries`, `fiche_salarie` et `embaucher`. La page de
connexion et son adresse sont fournies.

## Critères d'acceptation

1. Un accès anonyme est **redirigé** vers la connexion, jamais servi.
2. Après connexion, les trois pages répondent 200.
3. Un `POST` anonyme sur l'embauche ne crée rien.
