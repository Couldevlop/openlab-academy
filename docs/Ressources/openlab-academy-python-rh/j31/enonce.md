# Journée 31 — Challenge

Livrez le formulaire d'embauche.

## Ce qu'il faut écrire

- `EmbaucheForm` : les cinq champs du salarié, un matricule normalisé en majuscules et refusé
  s'il est déjà pris, quelle que soit la casse saisie, et une date d'embauche qui ne peut pas être
  dans le futur ;
- la vue `embaucher` : le formulaire en `GET`, l'enregistrement puis la redirection vers la fiche
  en `POST` valide, et la page réaffichée avec ses erreurs en `POST` invalide.

## Critères d'acceptation

1. Un `POST` invalide ne crée rien du tout, et réaffiche la page avec ses erreurs.
2. Un matricule déjà pris, même écrit autrement, est refusé.
3. Le formulaire porte la protection contre la falsification de requête.
