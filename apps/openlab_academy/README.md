# openlab_academy

Personnalisation OpenLab Academy pour Frappe LMS : habillage, parcours certifiants, cohortes.

## Développement

Banc de dev : conteneur `openlab-academy_frappe_1` (bench `/home/frappe/frappe-bench`, site `lms.localhost`).

```bash
bash docker/dev-sync.sh                     # copie l'app dans le bench
bench --site lms.localhost install-app openlab_academy
bench --site lms.localhost run-tests --app openlab_academy
```

## Architecture (Clean Architecture / DDD)

| Couche | Dossier | Rôle |
|---|---|---|
| Domaine | `domain/` | Entités `Parcours`, `Projet`, `Module` ; invariants ; plan des chapitres. Aucune dépendance. |
| Application | `application/` | Cas d'usage `PublierParcours` ; port `DepotCatalogue`. |
| Infrastructure | `infrastructure/` | Source YAML (`yaml_source`), rendu Editor.js (`editorjs`), adaptateur Frappe LMS (`depot_frappe`). |
| Entrée | `entrypoints/` | Commandes `bench execute` (racine de composition). |

Données : `data/parcours/*.yaml` (un fichier par parcours, 10 projets + 1 capstone obligatoires).

```bash
bash docker/dev-test.sh                     # tous les tests + couverture (seuil 99 %)
bench --site lms.localhost execute openlab_academy.entrypoints.seed.run
```

## Exploitation (image Docker)

```bash
cd docker
cp .env.example .env            # puis remplacer les mots de passe
docker-compose -p ol-academy build
docker-compose -p ol-academy up -d
```

- Premier démarrage : création du site `SITE_NAME`, installation de payments, lms et openlab_academy
  (réglages fr / Africa/Abidjan / XOF, publication des parcours, cohorte pilote standard).
- Redémarrages suivants : `bench migrate`, aucune recréation ; données dans les volumes `sites` et `mariadb-data`.
- Ouvrir une cohorte intensive (16 h/semaine) :
  `docker exec ol-academy_app_1 bench --site <site> execute openlab_academy.entrypoints.cohorte.ouvrir_pilote --kwargs "{'rythme': 'intensif'}"`
- Ajouter ou modifier un parcours : éditer `data/parcours/NN-<slug>.yaml` (10 projets + 1 capstone obligatoires),
  reconstruire l'image, puis `bench --site <site> execute openlab_academy.entrypoints.seed.run`.
  Un cours qui a déjà des inscrits n'est jamais modifié.
