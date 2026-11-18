# Journée 35 — Challenge

Finissez l'application, et montrez-la.

## Ce qu'il faut écrire

`config/production.py` : les réglages de mise en service, qui complètent ceux de développement.
La clé secrète vient de l'environnement et n'a aucune valeur de repli. La vérification de
déploiement ne doit plus rien signaler.

Puis : `DJANGO_SETTINGS_MODULE=config.production python manage.py check --deploy`.

## Critères d'acceptation

1. `check --deploy` ne signale aucune alerte.
2. La clé secrète est absente du dépôt, en développement comme en production.
3. Toute la suite de tests des journées précédentes passe encore.

## Le dernier geste

Montrez l'application à quelqu'un, et notez ses deux premières questions. C'est votre liste de
corrections pour demain.
