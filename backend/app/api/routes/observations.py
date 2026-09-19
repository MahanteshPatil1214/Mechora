"""Observation listing, retrieval, validation updates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.database import repos
from app.schemas.api import (
    ObservationList,
    ObservationOut,
    ValidationUpdate,
)

router = APIRouter(tags=["observations"])


def _to_out(obs) -> ObservationOut:
    return ObservationOut(
        id=obs.id,
        report_id=obs.report_id,
        narrative=obs.narrative,
        provider=obs.provider,
        resolved_provider=obs.provider,
        requested_provider=obs.requested_provider,
        fallback_used=obs.fallback_used,
        fallback_reason=obs.fallback_reason,
        event=obs.event,
        precursor_family_id=obs.precursor_family_id,
        validation=obs.validation,
        validation_reviewer=obs.validation_reviewer,
        validation_reason=obs.validation_reason,
        validated_at=obs.validated_at,
        created_at=obs.created_at,
    )


@router.get("/observations", response_model=ObservationList)
def list_observations(
    activity: str | None = Query(None),
    barrier: str | None = Query(None),
    barrier_state: str | None = Query(None),
    energy: str | None = Query(None),
    exposure: str | None = Query(None),
    location: str | None = Query(None),
    sif: str | None = Query(None),
    family_id: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> ObservationList:
    filters = repos.ObservationFilters(
        activity=activity or None,
        barrier=barrier or None,
        barrier_state=barrier_state or None,
        energy=energy or None,
        exposure=exposure or None,
        location=location or None,
        sif=sif or None,
        family_id=family_id or None,
        q=q or None,
        limit=limit,
        offset=offset,
    )
    rows = repos.list_observations(filters)
    return ObservationList(
        total=repos.count_observations(filters),
        observations=[_to_out(o) for o in rows],
    )


@router.get("/observations/{obs_id}", response_model=ObservationOut)
def get_observation(obs_id: str) -> ObservationOut:
    obs = repos.get_observation(obs_id)
    if obs is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return _to_out(obs)


@router.delete("/observations/{obs_id}", status_code=204)
def delete_observation(obs_id: str) -> None:
    """Delete an observation. Precursor families are rebuilt afterwards so
    membership lists and ``precursor_family_id`` back-references stay in sync."""
    if not repos.delete_observation(obs_id):
        raise HTTPException(status_code=404, detail="observation not found")


@router.patch("/observations/{obs_id}/validation", response_model=ObservationOut)
def update_validation(obs_id: str, body: ValidationUpdate) -> ObservationOut:
    obs = repos.update_validation(
        obs_id, body.status, reviewer=body.reviewer or "", reason=body.reason or ""
    )
    if obs is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return _to_out(obs)