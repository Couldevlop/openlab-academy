#!/usr/bin/env bash
# Démarrage d'un service de l'image : web (préparation du site puis gunicorn), socketio, worker ou schedule.
# Seul « web » prépare le site (création au premier lancement, migration ensuite) ; les autres attendent qu'il soit prêt.
# Mots de passe lus dans les secrets Docker (/run/secrets), jamais dans l'environnement du conteneur.
set -euo pipefail
: "${SITE_NAME:?SITE_NAME requis}"
cd /home/frappe/frappe-bench
SERVICE="${1:-web}"

secret() {
  local fichier="/run/secrets/$1"
  [ -r "$fichier" ] || { echo "Secret $1 absent (docker/secrets/$1.txt)" >&2; exit 1; }
  tr -d '\r\n' < "$fichier"
}

attendre_site() {
  until [ -f "sites/${SITE_NAME}/site_config.json" ] && [ -f sites/.pret ]; do
    echo "Attente de la préparation du site ${SITE_NAME}…"; sleep 3
  done
}

preparer() {
  rm -f sites/.pret
  cp -f /home/frappe/sites-image/apps.txt sites/apps.txt
  # assets recopiés seulement quand l'image a changé (même manifeste = mêmes fichiers compilés), ou quand le volume
  # garde des liens vers apps/ d'une image antérieure (illisibles pour nginx)
  if [ -L sites/assets/frappe ] || ! cmp -s /home/frappe/sites-image/assets/assets.json sites/assets/assets.json 2>/dev/null; then
    rm -rf sites/assets && cp -a /home/frappe/sites-image/assets sites/assets
  fi
  bench set-mariadb-host mariadb
  bench set-redis-cache-host redis://redis:6379
  bench set-redis-queue-host redis://redis:6379
  bench set-redis-socketio-host redis://redis:6379
  bench set-config -g socketio_port 9000
  until bash -c "</dev/tcp/mariadb/3306" 2>/dev/null; do echo "Attente de MariaDB…"; sleep 2; done
  if [ ! -f "sites/${SITE_NAME}/site_config.json" ]; then
    bench new-site "$SITE_NAME" --mariadb-root-password "$(secret db_root_password)" \
      --admin-password "$(secret admin_password)" --mariadb-user-host-login-scope='%'
  else
    bench --site "$SITE_NAME" migrate
  fi
  # Répare un premier démarrage interrompu : installe toute app attendue encore absente du site.
  installees="$(bench --site "$SITE_NAME" list-apps 2>/dev/null | awk '{print $1}')"
  for app in payments lms openlab_academy; do
    if ! grep -qx "$app" <<<"$installees"; then
      echo "Installation de $app sur $SITE_NAME"
      bench --site "$SITE_NAME" install-app "$app"
    fi
  done
  bench use "$SITE_NAME"
  bench --site "$SITE_NAME" enable-scheduler
  touch sites/.pret
}

case "$SERVICE" in
  web)
    preparer
    exec ./env/bin/gunicorn --chdir=sites --bind=0.0.0.0:8000 --worker-class=gthread \
      --workers="${GUNICORN_WORKERS:-2}" --threads="${GUNICORN_THREADS:-4}" --timeout=120 \
      --max-requests=2000 --max-requests-jitter=200 --access-logfile=- --preload frappe.app:application ;;
  socketio) attendre_site; exec node apps/frappe/socketio.js ;;
  worker)   attendre_site; exec bench worker --queue short,default,long ;;
  schedule) attendre_site; exec bench schedule ;;
  *) echo "Service inconnu : $SERVICE (web, socketio, worker, schedule)" >&2; exit 2 ;;
esac
