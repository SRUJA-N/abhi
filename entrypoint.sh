#!/bin/bash
set -e
cd /app



python <<'PY'
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from config.db_utils import wait_for_database

wait_for_database(20)
PY

python manage.py migrate --noinput
python manage.py seed_base_users

if command -v mysql >/dev/null 2>&1; then
  mysql -h"${MYSQL_HOST}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" < /app/init.sql
fi

exec python manage.py runserver 0.0.0.0:8000
