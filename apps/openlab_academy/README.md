# openlab_academy

Personnalisation OpenLab Academy pour Frappe LMS : habillage, parcours certifiants, cohortes.

## Développement

Banc de dev : conteneur `openlab-academy_frappe_1` (bench `/home/frappe/frappe-bench`, site `lms.localhost`).

```bash
bash docker/dev-sync.sh                     # copie l'app dans le bench
bench --site lms.localhost install-app openlab_academy
bench --site lms.localhost run-tests --app openlab_academy
```
