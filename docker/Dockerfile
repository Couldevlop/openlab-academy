# Image figée OpenLab Academy : Frappe (tag), payments et LMS (commits) épinglés + openlab_academy, assets compilés.
# Une seule image pour tous les services (docker-compose.yml) : web (gunicorn), socketio, worker, schedule ; le
# frontal nginx sert les fichiers statiques. Le serveur de développement (bench start) n'est plus utilisé.
FROM frappe/bench@sha256:1b27bb30ab18b0a50b5264f44988335bfe8e280a68b45d0ff2daf72ca6ddb85f
USER frappe
WORKDIR /home/frappe
ARG FRAPPE_REF=v15.123.1
ARG PAYMENTS_REF=9885a6e500104f1f160add47d55b370773e67a81
ARG LMS_REF=aa8b53b0a7e940871cdb006962a212daccb52a09
RUN yarn config set network-timeout 600000 -g \
 && bench init --frappe-branch "$FRAPPE_REF" --skip-redis-config-generation --skip-assets frappe-bench
WORKDIR /home/frappe/frappe-bench
RUN bench get-app --skip-assets payments --branch version-15  && (cd apps/payments && git fetch --depth 1 upstream "$PAYMENTS_REF" && git checkout -q -f "$PAYMENTS_REF") \
 && bench get-app --skip-assets lms --branch main \
 && cd apps/lms && git fetch --depth 1 upstream "$LMS_REF" && git checkout -q -f "$LMS_REF"
COPY --chown=frappe:frappe apps/openlab_academy apps/openlab_academy
# écrans d'évaluation (Vue 3 + frappe-ui) : construits vers openlab_academy/public/espace, dépendances retirées
RUN cd apps/openlab_academy/frontend \
 && npm ci --no-audit --no-fund \
 && npm run build \
 && rm -rf node_modules
RUN ./env/bin/pip install -q -e apps/openlab_academy \
 && printf "frappe\npayments\nlms\nopenlab_academy" > sites/apps.txt \
 && (cd apps/lms && yarn install --check-files) \
 && bench build --production \
 && cp -a sites /home/frappe/sites-image \
 && rm -rf /home/frappe/sites-image/assets \
 && cp -rL sites/assets /home/frappe/sites-image/assets
# assets en fichiers réels (liens vers apps/ résolus) : le frontal nginx n'a que le volume « sites », pas les apps
COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
EXPOSE 8000 9000
ENTRYPOINT ["bash", "/home/frappe/entrypoint.sh"]
CMD ["web"]
