#!/usr/bin/env bash
set -euo pipefail
C=openlab-academy_frappe_1
B=/home/frappe/frappe-bench
APP="$(cd "$(dirname "$0")/../apps/openlab_academy" && pwd)"
FRONT="$APP/frontend"
PAQUET="$APP/openlab_academy/public/espace/espace.js"
export MSYS_NO_PATHCONV=1
# écrans d'évaluation : dépendances installées au besoin, paquet reconstruit dès que ses sources changent (fichier
# ajouté, modifié ou supprimé : empreinte des chemins et des dates, gardée hors du paquet servi)
[ -d "$FRONT/node_modules" ] || (cd "$FRONT" && npm ci --no-audit --no-fund)
EMPREINTE="$FRONT/node_modules/.empreinte-espace"
SOURCES="$(cd "$FRONT" && find src package.json package-lock.json vite.config.ts tsconfig.json -type f -printf '%p %T@\n' | sort | sha1sum)"
if [ ! -f "$PAQUET" ] || [ "$(cat "$EMPREINTE" 2>/dev/null)" != "$SOURCES" ]; then
  (cd "$FRONT" && npm run --silent build)
  printf '%s' "$SOURCES" > "$EMPREINTE"
fi
docker exec -u frappe "$C" rm -rf "$B/apps/openlab_academy"
docker exec -u frappe "$C" mkdir -p "$B/apps/openlab_academy"
# copie sans les dépendances du frontend (node_modules), inutiles au serveur
tar -C "$APP" --exclude=./frontend/node_modules -cf - . | docker exec -i -u root "$C" tar -C "$B/apps/openlab_academy" -xf -
docker exec -u root "$C" chown -R frappe:frappe "$B/apps/openlab_academy"
docker exec -u frappe -w "$B" "$C" bash -lc '
  find apps/openlab_academy -name "__pycache__" -prune -exec rm -rf {} +
  ./env/bin/pip install -q -e apps/openlab_academy
  grep -qx openlab_academy sites/apps.txt || printf "\nopenlab_academy" >> sites/apps.txt
  # assets servis par le site (logo du bureau, feuilles de style) : lien refait a chaque copie, sinon 404 sur /assets
  ln -sfn "$PWD/apps/openlab_academy/openlab_academy/public" sites/assets/openlab_academy'
