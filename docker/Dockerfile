# Image figée OpenLab Academy : Frappe v15 + payments + LMS (commit pinné) + openlab_academy, assets compilés.
FROM frappe/bench@sha256:1b27bb30ab18b0a50b5264f44988335bfe8e280a68b45d0ff2daf72ca6ddb85f
USER frappe
WORKDIR /home/frappe
ARG LMS_REF=aa8b53b0a7e940871cdb006962a212daccb52a09
RUN yarn config set network-timeout 600000 -g \
 && bench init --frappe-branch version-15 --skip-redis-config-generation --skip-assets frappe-bench
WORKDIR /home/frappe/frappe-bench
RUN bench get-app --skip-assets payments --branch version-15 \
 && bench get-app --skip-assets lms --branch main \
 && cd apps/lms && git fetch --depth 1 upstream "$LMS_REF" && git checkout -q -f "$LMS_REF"
COPY --chown=frappe:frappe apps/openlab_academy apps/openlab_academy
RUN ./env/bin/pip install -q -e apps/openlab_academy \
 && printf "frappe\npayments\nlms\nopenlab_academy" > sites/apps.txt \
 && (cd apps/lms && yarn install --check-files) \
 && bench build --production \
 && sed -i '/redis/d;/watch/d' Procfile \
 && cp -a sites /home/frappe/sites-image
COPY --chown=frappe:frappe docker/entrypoint.sh /home/frappe/entrypoint.sh
EXPOSE 8000 9000
ENTRYPOINT ["bash", "/home/frappe/entrypoint.sh"]
