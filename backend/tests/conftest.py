"""Shared test fixtures.

MECHORA always runs on its own temp SQLite file during tests. Environment
variables are set before any ``app`` import so ``pydantic-settings`` picks up
the offline store.
"""

from __future__ import annotations

import os
import pathlib
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="mechora_tests_")
_DB_FILE = pathlib.Path(_TMP) / "test.db"

os.environ["STORE"] = "sqlite"
os.environ["SQLITE_FALLBACK_PATH"] = str(_DB_FILE)
os.environ["EXTRACTION_PROVIDER"] = "rules"


@pytest.fixture(autouse=True)
def _fresh_database():
    """Reset DB state before every test (offline SQLite)."""
    if _DB_FILE.exists():
        _DB_FILE.unlink()
    for suffix in ("-wal", "-shm"):
        p = pathlib.Path(str(_DB_FILE) + suffix)
        if p.exists():
            p.unlink()
    from app.config import get_settings

    get_settings.cache_clear()
    from app.database import engine as db_engine

    db_engine.dispose()
    db_engine.init_db()
    yield
    db_engine.dispose()