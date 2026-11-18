# Ressources livrées avec l'application

Archives jointes aux leçons en **fichiers privés** : elles ne sont servies qu'aux membres dont le parcours n'est ni
fermé, ni caché, ni bloqué, et dont la leçon est accessible (contrôle des médias de leçon,
`entrypoints/lms.py: serve_resource`). Une leçon les cite par la clé `archive:` de son module, qui n'accepte qu'un
nom de fichier `.zip`, jamais un chemin.

## `socle-ia-agentique-v0.3.0.zip`

Dépôt de départ du parcours « IA agentique », produit à partir de
`docs/Ressources/openlab-academy-agentic-starter/` après les corrections de lint du 12 novembre 2026. Les supports
de séance du formateur (`docs/TP_SEANCE_*.md`, `docs/SUPPORTS.md`) en sont **exclus** : l'apprenant reçoit le brief,
la grille de revue, la progression, le rapport de validation et le code, pas les déroulés minutés ni les indices.

Reconstruction, depuis la racine du projet :

```bash
python docs/Ressources/construire_archive_socle.py
```

Le script écrit l'archive dans ce dossier et affiche son empreinte. Toute évolution du socle demande de la
reconstruire, puis de republier le parcours pour que la leçon cite la nouvelle version.
