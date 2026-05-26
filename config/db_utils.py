"""
Database handshake: retry connecting to MySQL for up to ``max_seconds`` (default 20).
Used by WSGI/ASGI and management entrypoints so the app waits for containerized MySQL.
"""
from __future__ import annotations

import time
from typing import NoReturn

from django.db import connection
from django.db.utils import OperationalError


def wait_for_database(max_seconds: int = 20, interval_seconds: float = 1.0) -> None:
    """Wait for DB availability.

    For SQLite (local/dev) there is no external handshake, so this becomes a no-op.
    """
    if connection.vendor == "sqlite":
        return

    deadline = time.monotonic() + float(max_seconds)

    last_error: OperationalError | None = None
    while time.monotonic() < deadline:
        try:
            connection.close_if_unusable_or_obsolete()
            connection.ensure_connection()
            return
        except OperationalError as exc:
            last_error = exc
            time.sleep(interval_seconds)
    _raise_wait_failure(last_error, max_seconds)


def _raise_wait_failure(last_error: OperationalError | None, max_seconds: int) -> NoReturn:
    if last_error is not None:
        raise OperationalError(
            f"MySQL not reachable after {max_seconds}s: {last_error}"
        ) from last_error
    raise OperationalError(f"MySQL not reachable after {max_seconds}s (unknown error)")
