#!/usr/bin/env bash
# Démarrage : rafraîchit apps.txt et assets depuis l'image, crée le site au premier lancement, puis démarre.
set -euo pipefail
: "${SITE_NAME:?SITE_NAME requis}" "${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD requis}" "${ADMIN_PASSWORD:?ADMIN_PASSWORD requis}"
cd /home/frappe/frappe-bench
cp -f /home/frappe/sites-image/apps.txt sites/apps.txt
rm -rf sites/assets && cp -a /home/frappe/sites-image/assets sites/assets
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379
until bash -c "</dev/tcp/mariadb/3306" 2>/dev/null; do echo "Attente de MariaDB…"; sleep 2; done
if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
  bench new-site "$SITE_NAME" --mariadb-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" --mariadb-user-host-login-scope='%'
  for app in payments lms openlab_academy; do bench --site "$SITE_NAME" install-app "$app"; done
else
  bench --site "$SITE_NAME" migrate
fi
bench use "$SITE_NAME"
exec bench start
