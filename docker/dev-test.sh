#!/usr/bin/env bash
# Usage : bash docker/dev-test.sh [module]   (ex. openlab_academy.tests.test_schema)
# Lance les tests avec mesure de couverture (seuil 99 % sur openlab_academy, hors tests).
set -uo pipefail
bash "$(dirname "$0")/dev-sync.sh"
ARGS="--app openlab_academy"
[ $# -gt 0 ] && ARGS="--module $1"
MSYS_NO_PATHCONV=1 docker exec -u frappe -w /home/frappe/frappe-bench/sites openlab-academy_frappe_1 bash -lc "
  ../env/bin/python -c 'import coverage' 2>/dev/null || ../env/bin/pip install -q coverage
  ../env/bin/coverage run --branch --source=../apps/openlab_academy/openlab_academy \
    --omit='*/tests/*,*/hooks.py' -m frappe.utils.bench_helper frappe --site lms.localhost \
    run-tests --skip-before-tests $ARGS > /tmp/tests.log 2>&1
  status=\$?
  grep -E '^(Ran|OK|FAILED)|^(FAIL|ERROR):|Error: |line [0-9]+, in test' /tmp/tests.log | head -30
  ../env/bin/coverage report -m --skip-covered --fail-under=99 2>&1 | tail -8
  cov=\$?
  exit \$(( status || cov ))"
