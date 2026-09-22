"""CAPA (Corrective And Preventive Action) endpoints.

Mirrors the **flat** ``app.models.capa.CAPA`` surface exactly: every payload is
a lossless round-trip of the persisted row PRESENT AT READ TIME. All
``effectiveness_*`` fields are served precomputed from the deterministic
evidence rule engine (``app.services.capa.effectiveness``) and persisted via
``repos`` -- we never fabricate a score or a basis string here.
"""

from __future__ import annotations

from typing import Any

import datetime as _dt

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import repos
from app.models.capa import BaselineSnapshot, CAPA
from app.schemas.api import (
    CapaCreate,
    CapaEffectivenessUpdate,
    CapaList,
    CapaOut,
    CapaStatusUpdate,
)
from app.security.auth import require_auth

router = APIRouter(tags=["capas"], dependencies=[Depends(require_auth)])


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _to_out(capa: CAPA) -> CapaOut:
    return CapaOut(
        id=capa.id,
        report_id=capa.report_id,
        title=capa.title,
        description=capa.description,
        linked_barrier_id=capa.linked_barrier_id,
        location=capa.location,
        site=capa.site,
        status=capa.status,
        created_at=capa.created_at,
        closed_at=capa.closed_at,
        baseline=capa.baseline.model_dump(mode="json") if capa.baseline else None,
        post_capa=capa.post_capa.model_dump(mode="json") if capa.post_capa else None,
        effectiveness_status=capa.effectiveness_status,
        effectiveness_basis=capa.effectiveness_basis,
        evidence_observation_ids=list(capa.evidence_observation_ids),
    )


@router.get("/capas", response_model=CapaList)
def list_capas(
    status: str | None = Query(default=None),
    linked_barrier_id: str | None = Query(default=None, alias="linked_barrier_id"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List persisted CAPAs, optionally filtered by status / linked barrier."""
    rows = repos.list_capas(
        status=status,
        barrier=linked_barrier_id,
        limit=limit,
        offset=offset,
    )
    return {
        "capas": [_to_out(c) for c in rows],
        "total": repos.count_capas(status=status, barrier=linked_barrier_id),
        "limit": limit,
        "offset": offset,
    }


@router.get("/capas/{capa_id}", response_model=CapaOut)
def get_capa(capa_id: str) -> CapaOut:
    capa = repos.get_capa(capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return _to_out(capa)


@router.post("/capas", response_model=CapaOut, status_code=201)
def create_capa(payload: CapaCreate) -> CapaOut:
    """Create a CAPA targeted at one linked barrier.

    ``repos.create_capa`` runs the deterministic effectiveness engine
    immediately, so the returned row already carries correct
    ``effectiveness_status`` and baseline evidence. No synthetic basis text is
    ever generated.
    """
    capa = repos.create_capa(
        CAPA(
            report_id=payload.report_id,
            title=payload.title,
            description=payload.description,
            linked_barrier_id=payload.linked_barrier_id,
            location=payload.location,
            site=payload.site,
            status=payload.status,
            baseline=BaselineSnapshot(window_days=payload.window_days),
            created_at=payload.created_at or _now_iso(),
        )
    )
    return _to_out(capa)


@router.post("/capas/{capa_id}/status", response_model=CapaOut)
def update_capa_status(capa_id: str, payload: CapaStatusUpdate) -> CapaOut:
    """Transit a CAPA status (open -> in_progress -> closed).

    Closing persists ``closed_at`` (defaults to now) and then recomputes the
    post-CAPA effectiveness window deterministically, so recurrence evidence
    begins counting at this moment.
    """
    existing = repos.get_capa(capa_id)
    if not existing:
        raise HTTPException(status_code=404, detail="CAPA not found")

    closed_at = payload.closed_at
    if payload.status == "closed" and not closed_at:
        closed_at = _now_iso()

    updated = repos.update_capa_status(capa_id, payload.status, closed_at=closed_at)
    if not updated:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return _to_out(updated)


@router.put("/capas/{capa_id}/effectiveness", response_model=CapaOut)
def update_capa_effectiveness(
    capa_id: str, payload: CapaEffectivenessUpdate
) -> CapaOut:
    """Persist a human-reviewed effectiveness update (status + optional basis).

    Stores exactly what the operator sends alongside the CAPA's own persisted
    ``post_capa`` evidence; it never fabricates anything on its own. Pass
    ``evidence_observation_ids`` only when you want to pin the evidence list
    used as the effectiveness basis.
    """
    existing = repos.get_capa(capa_id)
    if not existing:
        raise HTTPException(status_code=404, detail="CAPA not found")

    updated = repos.update_capa_effectiveness(
        capa_id=capa_id,
        effectiveness_status=payload.effectiveness_status,
        effectiveness_basis=payload.effectiveness_basis,
        post_capa=(
            existing.post_capa.model_dump(mode="json")
            if existing.post_capa
            else None
        ),
        evidence_observation_ids=payload.evidence_observation_ids,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return _to_out(updated)


@router.delete("/capas/{capa_id}", status_code=204)
def delete_capa(capa_id: str) -> None:
    if not repos.delete_capa(capa_id):
        raise HTTPException(status_code=404, detail="CAPA not found")
