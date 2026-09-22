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
    import gc
    import time

    from app.database import engine as db_engine

    def _unlink(path: pathlib.Path) -> None:
        # On Windows, WAL file handles held by disposed SQLAlchemy connections
        # can linger until GC; retry briefly before giving up.
        for _ in range(20):
            try:
                path.unlink()
                return
            except FileNotFoundError:
                return
            except PermissionError:
                db_engine.dispose()
                gc.collect()
                time.sleep(0.05)
        path.unlink()

    db_engine.dispose()
    gc.collect()
    _unlink(_DB_FILE)
    for suffix in ("-wal", "-shm"):
        _unlink(pathlib.Path(str(_DB_FILE) + suffix))
    from app.config import get_settings

    get_settings.cache_clear()
    db_engine.init_db()
    yield
    db_engine.dispose()