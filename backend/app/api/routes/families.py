"""Precursor family + dashboard + aggregate endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.database import repos
from app.schemas.api import (
    DashboardOut,
    FamilyList,
    FamilyOut,
)

router = APIRouter(tags=["families", "dashboard"])


def _to_out(fam) -> FamilyOut:
    return FamilyOut(
        id=fam.id,
        name=fam.name,
        description=fam.description,
        observation_ids=fam.observation_ids,
        common_barrier=fam.common_barrier,
        common_barrier_state=fam.common_barrier_state,
        common_energy=fam.common_energy,
        common_exposure=fam.common_exposure,
        activities=list(fam.activities or []),
        locations=list(fam.locations or []),
        hazard=fam.hazard,
        attention_signal=fam.attention_signal,
        attention_basis=list(fam.attention_basis or []),
        attention_factors=list(fam.attention_factors or []),
        sif_potential_count=fam.sif_potential_count,
        recurring=bool(fam.recurring),
        recurring_threshold=fam.recurring_threshold or 2,
        grouping_evidence=[g.model_dump() for g in fam.grouping_evidence],
        exclusions=[e.model_dump() for e in fam.exclusions],
        created_at=fam.created_at,
    )


@router.get("/families", response_model=FamilyList)
def list_families(
    recurring_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
) -> FamilyList:
    families = repos.list_families(recurring_only=recurring_only, limit=limit)
    recurring = sum(1 for f in families if f.recurring)
    return FamilyList(
        total=len(families),
        recurring=recurring,
        families=[_to_out(f) for f in families],
    )


@router.get("/families/{fam_id}", response_model=FamilyOut)
def get_family(fam_id: str) -> FamilyOut:
    fam = repos.get_family(fam_id)
    if fam is None:
        raise HTTPException(status_code=404, detail="family not found")
    return _to_out(fam)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard() -> DashboardOut:
    return DashboardOut(**repos.dashboard_summary())


@router.get("/aggregates/{kind}")
def aggregates(kind: str) -> list[dict]:
    if kind == "barrier":
        return repos.barrier_aggregates()
    if kind == "activity":
        return repos.activity_aggregates()
    if kind == "location":
        return repos.location_aggregates()
    if kind == "lsr":
        return repos.lsr_aggregates()
    if kind == "sif":
        return repos.sif_aggregates()
    raise HTTPException(status_code=404, detail=f"unknown aggregate kind: {kind}")