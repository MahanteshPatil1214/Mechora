"""SQLAlchemy engine/session management (Postgres default, SQLite fallback)."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("mechora.database")


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker | None = None
_backend_used = ""


def _create(url: str, *, fallback: bool = False) -> tuple[Engine, str]:
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        return engine, "sqlite"

    engine = create_engine(url, pool_pre_ping=True)
    return engine, "postgresql"


def init_db() -> None:
    """Build the engine/session factory, applying the store policy."""
    global _engine, _session_factory, _backend_used

    settings = get_settings()
    mode = (settings.store or "auto").lower()

    if mode == "sqlite":
        _engine, _backend_used = _create(settings.sqlite_fallback_url
                                         if not settings.database_url.startswith("sqlite")
                                         else settings.database_url)
        logger.warning("MECHORA store: SQLite (offline mode).")
    elif mode == "postgres":
        _engine, _backend_used = _create(settings.database_url)
        logger.info("MECHORA store: PostgreSQL.")
    else:  # auto
        try:
            _engine, _backend_used = _create(settings.database_url)
            with _engine.connect():
                pass  # reachability probe
            logger.info("MECHORA store: PostgreSQL.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "PostgreSQL unavailable (%s); falling back to SQLite.", exc
            )
            _engine, _backend_used = _create(settings.sqlite_fallback_url)

    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)

    # Import models here so tables are registered before create_all.
    from app.database import tables  # noqa: F401
    Base.metadata.create_all(_engine)


def get_session() -> Session:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory()


def backend_name() -> str:
    return _backend_used or "not-initialized"


def dispose() -> None:
    global _engine, _session_factory, _backend_used
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
    _backend_used = ""