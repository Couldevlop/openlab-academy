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
