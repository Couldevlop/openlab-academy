#!/usr/bin/env bash
# Usage : bash docker/dev-test.sh [module]   (ex. openlab_academy.tests.test_schema)
# Lance les tests avec mesure de couverture (seuil 99 % sur openlab_academy, hors tests).
#
# Le seuil ne porte que sur la suite entière. Un module seul n'exerce que quelques pour cent du
# code : lui appliquer 99 % rendait tout lancement ciblé rouge, et un vrai échec de test n'y était
# plus discernable du bruit. Or le lancement ciblé est le seul que la mémoire d'un poste de
# développement autorise, la suite complète demandant trois quarts d'heure et plusieurs gigaoctets.
set -uo pipefail
bash "$(dirname "$0")/dev-sync.sh"
ARGS="--app openlab_academy"
SEUIL="--fail-under=99"
if [ $# -gt 0 ]; then
  ARGS="--module $1"
  SEUIL=""
fi
MSYS_NO_PATHCONV=1 docker exec -u frappe -w /home/frappe/frappe-bench/sites openlab-academy_frappe_1 bash -lc "
  # \`bash -lc\` ouvre un shell neuf, qui n'hérite pas du \`pipefail\` posé plus haut : sans cette
  # ligne, le code lu dans \$cov était celui de \`tail\` et valait toujours zéro. Le seuil de
  # couverture était annoncé sur la sortie, puis jamais appliqué — ce script ne pouvait pas échouer
  # sur une couverture insuffisante. La barrière des 99 % de la chaîne d'intégration, elle, fait sa
  # propre mesure et n'a jamais dépendu d'ici.
  set -o pipefail
  ../env/bin/python -c 'import coverage' 2>/dev/null || ../env/bin/pip install -q coverage
  ../env/bin/coverage run --branch --source=../apps/openlab_academy/openlab_academy \
    --omit='*/tests/*,*/hooks.py' -m frappe.utils.bench_helper frappe --site lms.localhost \
    run-tests --skip-before-tests $ARGS > /tmp/tests.log 2>&1
  status=\$?
  grep -E '^(Ran|OK|FAILED)|^(FAIL|ERROR):|Error: |line [0-9]+, in test' /tmp/tests.log | head -30
  ../env/bin/coverage report -m --skip-covered $SEUIL 2>&1 | tail -8
  cov=\$?
  exit \$(( status || cov ))"
