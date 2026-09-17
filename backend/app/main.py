"""MECHORA FastAPI application entrypoint.

Runs with the offline SQLite store by default (PostgreSQL optional).
Health, analyze, observations, families, dashboard, aggregates, ontology
reference and evaluation metrics are exposed under the configured prefix.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, families, health, observations, ontology
from app.config import get_settings
from app.database.engine import backend_name, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mechora.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("MECHORA backend=%s", backend_name())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Deterministic HSE precursor-attention engine for pipeline "
            "safety observation narratives (decision support only)."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_v1_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(analyze.router, prefix=prefix)
    app.include_router(observations.router, prefix=prefix)
    app.include_router(families.router, prefix=prefix)
    app.include_router(ontology.router, prefix=prefix)

    @app.get("/")
    def root() -> dict:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "api_prefix": prefix,
            "backend": backend_name() or "initializing",
        }

    return app


app = create_app()