#!/usr/bin/env bash
set -euo pipefail
C=openlab-academy_frappe_1
B=/home/frappe/frappe-bench
SRC="$(cd "$(dirname "$0")/../apps/openlab_academy" && (pwd -W 2>/dev/null || pwd))"
export MSYS_NO_PATHCONV=1
docker exec -u frappe "$C" rm -rf "$B/apps/openlab_academy"
docker cp "$SRC" "$C:$B/apps/openlab_academy"
docker exec -u root "$C" chown -R frappe:frappe "$B/apps/openlab_academy"
docker exec -u frappe -w "$B" "$C" bash -lc '
  find apps/openlab_academy -name "__pycache__" -prune -exec rm -rf {} +
  ./env/bin/pip install -q -e apps/openlab_academy
  grep -qx openlab_academy sites/apps.txt || printf "\nopenlab_academy" >> sites/apps.txt'
