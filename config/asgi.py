"""
ASGI config — applies MySQL handshake retry before exposing the application object.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from config.db_utils import wait_for_database

wait_for_database(max_seconds=20)

from django.core.asgi import get_asgi_application

application = get_asgi_application()
