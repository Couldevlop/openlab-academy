# Journée 34 — Challenge

Écrivez `python manage.py importer_effectif fichier.csv`.

## Ce qu'il faut écrire

La commande lit le fichier, crée les postes manquants, écrit les salariés absents de la base et
ignore ceux dont le matricule existe déjà. Elle dit combien de fiches ont été créées et combien
ont été ignorées.

Un fichier introuvable, une colonne absente ou un salaire illisible arrêtent la commande avec un
message qui dit quoi corriger.

## Critères d'acceptation

1. Relancer la commande sur le même fichier ne crée aucun doublon.
2. La masse salariale obtenue en base égale celle que le cœur Python pur calcule sur le fichier.
3. Un fichier fautif arrête la commande sans rien écrire à moitié.
