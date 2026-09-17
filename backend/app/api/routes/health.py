"""Health + metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.database.engine import backend_name

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.1.0",
        "backend": backend_name() or "not-initialized",
        "provider": settings.extraction_provider,
        "database_url": "(configured)" if settings.database_url else "none",
    }