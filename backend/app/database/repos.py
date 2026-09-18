"""Persistence repository layer.

All database access for the application. Family (re)assignment happens in a
single transaction: observations are recomputed structurally and family rows
are rebuilt, keeping ``report_id``/``observation_id`` references consistent.
"""

from __future__ import annotations

import datetime as _dt
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.engine import get_session
from app.database.tables import (
    EvaluationResultRow,
    ObservationRow,
    OntologyDocRow,
    PrecursorFamilyRow,
)
from app.models.safety_event import Observation, PrecursorFamily
from app.services.precursor.engine import PrecursorEngine


def new_observation_id() -> str:
    return "OBS-" + uuid.uuid4().hex[:10].upper()


def _obs_to_row(obs: Observation) -> ObservationRow:
    ev = obs.event
    return ObservationRow(
        id=obs.id,
        report_id=obs.report_id,
        narrative=obs.narrative,
        provider=obs.provider,
        event=json.loads(ev.model_dump_json()),
        activity=ev.activity,
        task_phase=ev.task_phase,
        barrier=ev.barrier,
        barrier_state=ev.barrier_state,
        energy=ev.energy,
        exposure=ev.exposure,
        location=ev.location,
        potential_consequence=ev.potential_consequence,
        sif_classification=ev.sif.classification,
        life_saving_rules=ev.life_saving_rules,
        precursor_family_id=obs.precursor_family_id,
        validation=obs.validation,
        created_at=obs.created_at,
    )


def _row_to_obs(row: ObservationRow) -> Observation:
    event = json.loads(json.dumps(row.event))
    from app.models.safety_event import SafetyEvent

    return Observation(
        id=row.id,
        report_id=row.report_id,
        narrative=row.narrative,
        provider=row.provider,
        event=SafetyEvent.model_validate(event),
        precursor_family_id=row.precursor_family_id,
        validation=row.validation,
        created_at=row.created_at,
    )


def _fam_to_row(fam: PrecursorFamily) -> PrecursorFamilyRow:
    return PrecursorFamilyRow(
        id=fam.id,
        name=fam.name,
        family_type=fam.family_type,
        description=fam.description,
        recurring=fam.recurring,
        common_barrier=fam.common_barrier,
        common_barrier_state=fam.common_barrier_state,
        common_energy=fam.common_energy,
        common_exposure=fam.common_exposure,
        core_mechanism=fam.core_mechanism,
        context=fam.context,
        recurrence=fam.recurrence,
        why_it_matters=fam.why_it_matters,
        activities=fam.activities,
        locations=fam.locations,
        observation_ids=fam.observation_ids,
        hazard=fam.hazard,
        attention_signal=fam.attention_signal,
        attention_basis=fam.attention_basis,
        attention_factors=fam.attention_factors,
        sif_potential_count=fam.sif_potential_count,
        recurring_threshold=fam.recurring_threshold,
        grouping_evidence=[g.model_dump() for g in fam.grouping_evidence],
        exclusions=[e.model_dump() for e in fam.exclusions],
        created_at=fam.created_at,
    )


def _row_to_fam(row: PrecursorFamilyRow) -> PrecursorFamily:
    from app.models.safety_event import ExclusionEntry, GroupingEvidence

    return PrecursorFamily(
        id=row.id,
        name=row.name,
        family_type=getattr(row, "family_type", "precursor") or "precursor",
        description=row.description,
        observation_ids=list(row.observation_ids or []),
        common_barrier=row.common_barrier,
        common_barrier_state=row.common_barrier_state,
        common_energy=row.common_energy,
        common_exposure=row.common_exposure,
        core_mechanism=getattr(row, "core_mechanism", {}) or {},
        context=getattr(row, "context", {}) or {},
        recurrence=getattr(row, "recurrence", {}) or {},
        why_it_matters=getattr(row, "why_it_matters", "") or "",
        activities=list(row.activities or []),
        locations=list(row.locations or []),
        hazard=row.hazard or "",
        attention_signal=row.attention_signal,
        attention_basis=list(row.attention_basis or []),
        attention_factors=list(row.attention_factors or []),
        sif_potential_count=row.sif_potential_count,
        recurring=bool(row.recurring),
        recurring_threshold=row.recurring_threshold or 2,
        grouping_evidence=[
            GroupingEvidence.model_validate(g) for g in (row.grouping_evidence or [])
        ],
        exclusions=[
            ExclusionEntry.model_validate(e) for e in (row.exclusions or [])
        ],
        created_at=row.created_at,
    )


@dataclass
class ObservationFilters:
    activity: str | None = None
    barrier: str | None = None
    barrier_state: str | None = None
    energy: str | None = None
    exposure: str | None = None
    location: str | None = None
    sif: str | None = None
    family_id: str | None = None
    q: str | None = None
    limit: int = 100
    offset: int = 0


def apply_observation_filters(stmt, filters: ObservationFilters):
    if filters.activity:
        stmt = stmt.where(ObservationRow.activity == filters.activity)
    if filters.barrier:
        stmt = stmt.where(ObservationRow.barrier == filters.barrier)
    if filters.barrier_state:
        stmt = stmt.where(ObservationRow.barrier_state == filters.barrier_state)
    if filters.energy:
        stmt = stmt.where(ObservationRow.energy == filters.energy)
    if filters.exposure:
        stmt = stmt.where(ObservationRow.exposure == filters.exposure)
    if filters.location:
        stmt = stmt.where(ObservationRow.location == filters.location)
    if filters.sif:
        stmt = stmt.where(ObservationRow.sif_classification == filters.sif)
    if filters.family_id:
        stmt = stmt.where(ObservationRow.precursor_family_id == filters.family_id)
    if filters.q:
        like = f"%{filters.q}%"
        stmt = stmt.where(
            ObservationRow.narrative.ilike(like) | ObservationRow.report_id.ilike(like)
        )
    return stmt


# ------------------------------------------------------------------ CRUD


def create_observation(obs: Observation, recompute: bool = True) -> Observation:
    if not obs.id:
        obs.id = new_observation_id()
    with get_session() as s:
        s.add(_obs_to_row(obs))
        s.commit()
    if recompute:
        recompute_families()
        # refresh family id from DB
        with get_session() as s:
            row = s.get(ObservationRow, obs.id)
            return _row_to_obs(row) if row else obs
    return obs


def bulk_create_observations(observations: list[Observation]) -> int:
    if not observations:
        return 0
    with get_session() as s:
        for obs in observations:
            existing = s.query(ObservationRow).filter_by(
                report_id=obs.report_id
            ).first()
            if existing:
                continue
            if not obs.id:
                obs.id = new_observation_id()
            s.add(_obs_to_row(obs))
        s.commit()
    recompute_families()
    return len(observations)


def get_observation(obs_id: str) -> Observation | None:
    with get_session() as s:
        row = s.get(ObservationRow, obs_id)
        return _row_to_obs(row) if row else None


def get_observation_by_report_id(report_id: str) -> Observation | None:
    with get_session() as s:
        row = s.query(ObservationRow).filter_by(report_id=report_id).first()
        return _row_to_obs(row) if row else None


def list_observations(
    filters: ObservationFilters | None = None,
) -> list[Observation]:
    filters = filters or ObservationFilters()
    with get_session() as s:
        stmt = select(ObservationRow).order_by(ObservationRow.created_at.desc())
        stmt = apply_observation_filters(stmt, filters)
        rows = s.execute(
            stmt.limit(filters.limit).offset(filters.offset)
        ).scalars().all()
        return [_row_to_obs(r) for r in rows]


def count_observations(filters: ObservationFilters | None = None) -> int:
    with get_session() as s:
        stmt = select(func.count()).select_from(ObservationRow)
        if filters:
            stmt = apply_observation_filters(stmt, filters)
        return int(s.execute(stmt).scalar_one())


def update_validation(obs_id: str, status: str) -> Observation | None:
    with get_session() as s:
        row = s.get(ObservationRow, obs_id)
        if not row:
            return None
        row.validation = status
        s.commit()
        return _row_to_obs(row)


def all_observations_ordered() -> list[Observation]:
    with get_session() as s:
        rows = s.execute(
            select(ObservationRow).order_by(ObservationRow.created_at.asc())
        ).scalars().all()
        return [_row_to_obs(r) for r in rows]


# ------------------------------------------------------------------ Families


def recompute_families(engine: Any = None) -> int:
    """Rebuild precursor families across all observations (single transaction)."""
    from app.config import get_settings
    from app.services.normalization.ontology import get_ontology

    observations = all_observations_ordered()
    if not observations:
        with get_session() as s:
            s.execute(delete(PrecursorFamilyRow))
            s.commit()
        return 0

    precursor = PrecursorEngine(get_ontology(), get_settings())
    families, assignment = precursor.run(observations)

    family_ids = [f.id for f in families]
    with get_session() as s:
        s.execute(delete(PrecursorFamilyRow))
        for fam in families:
            s.add(_fam_to_row(fam))
        rows = s.execute(select(ObservationRow)).scalars().all()
        for row in rows:
            row.precursor_family_id = assignment.get(row.id)
        s.commit()
    return len(families)


def list_families(recurring_only: bool = False, limit: int = 200) -> list[PrecursorFamily]:
    with get_session() as s:
        stmt = select(PrecursorFamilyRow).order_by(
            PrecursorFamilyRow.attention_signal.desc()
        )
        if recurring_only:
            stmt = stmt.where(PrecursorFamilyRow.recurring.is_(True))
        rows = s.execute(stmt.limit(limit)).scalars().all()
        return [_row_to_fam(r) for r in rows]


def get_family(fam_id: str) -> PrecursorFamily | None:
    with get_session() as s:
        row = s.get(PrecursorFamilyRow, fam_id)
        return _row_to_fam(row) if row else None


# ------------------------------------------------------------------ Dashboard


def dashboard_summary() -> dict[str, Any]:
    with get_session() as s:
        total = int(
            s.execute(select(func.count()).select_from(ObservationRow)).scalar_one()
        )
        sif_high = int(
            s.execute(
                select(func.count())
                .select_from(ObservationRow)
                .where(ObservationRow.sif_classification.in_(["high", "medium"]))
            ).scalar_one()
        )
        families = int(
            s.execute(select(func.count()).select_from(PrecursorFamilyRow)).scalar_one()
        )
        recurring = int(
            s.execute(
                select(func.count())
                .select_from(PrecursorFamilyRow)
                .where(PrecursorFamilyRow.recurring.is_(True))
            ).scalar_one()
        )
        barrier_failures = int(
            s.execute(
                select(func.count())
                .select_from(ObservationRow)
                .where(
                    ObservationRow.barrier_state.in_(
                        ["not_verified", "failed", "absent", "partially_effective"]
                    )
                )
            ).scalar_one()
        )
        locations_affected = len(
            s.execute(
                select(ObservationRow.location)
                .where(ObservationRow.location != "unknown")
                .distinct()
            ).scalars().all()
        )
        activities_affected = len(
            s.execute(
                select(ObservationRow.activity)
                .where(ObservationRow.activity != "unknown")
                .distinct()
            ).scalars().all()
        )
        return {
            "total_observations": total,
            "sif_potential_observations": sif_high,
            "precursor_families": families,
            "recurring_precursor_families": recurring,
            "recurring_barrier_failures": barrier_failures,
            "locations_affected": locations_affected,
            "activities_affected": activities_affected,
            "backend": backend_name(),
        }


def barrier_aggregates() -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(
            select(
                ObservationRow.barrier,
                ObservationRow.barrier_state,
                func.count().label("count"),
            )
            .group_by(ObservationRow.barrier, ObservationRow.barrier_state)
            .order_by(func.count().desc())
        ).all()
        return [
            {"barrier": b, "barrier_state": st, "count": int(c)}
            for b, st, c in rows
        ]


def activity_aggregates() -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(
            select(ObservationRow.activity, func.count().label("count"))
            .where(ObservationRow.activity != "unknown")
            .group_by(ObservationRow.activity)
            .order_by(func.count().desc())
        ).all()
        return [{"activity": a, "count": int(c)} for a, c in rows]


def location_aggregates() -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(
            select(ObservationRow.location, func.count().label("count"))
            .where(ObservationRow.location != "unknown")
            .group_by(ObservationRow.location)
            .order_by(func.count().desc())
        ).all()
        return [{"location": l, "count": int(c)} for l, c in rows]


def lsr_aggregates() -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(select(ObservationRow.life_saving_rules)).scalars().all()
    counter: dict[str, int] = {}
    for rules in rows:
        for r in rules or []:
            counter[r] = counter.get(r, 0) + 1
    return [{"life_saving_rule": r, "count": c}
            for r, c in sorted(counter.items(), key=lambda kv: -kv[1])]


def sif_aggregates() -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(
            select(ObservationRow.sif_classification, func.count().label("count"))
            .group_by(ObservationRow.sif_classification)
        ).all()
        return [{"classification": c, "count": int(n)} for c, n in rows]


# ------------------------------------------------------------------ Evaluation


def save_evaluation(run_id: str, metrics: dict, categories: dict,
                    counts: dict) -> None:
    with get_session() as s:
        existing = s.query(EvaluationResultRow).filter_by(run_id=run_id).first()
        if existing:
            existing.metrics = metrics
            existing.categories = categories
            existing.counts = counts
            existing.created_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        else:
            s.add(
                EvaluationResultRow(
                    run_id=run_id,
                    metrics=metrics,
                    categories=categories,
                    counts=counts,
                )
            )
        s.commit()


def latest_evaluation() -> dict[str, Any] | None:
    with get_session() as s:
        row = s.execute(
            select(EvaluationResultRow).order_by(EvaluationResultRow.id.desc())
        ).scalars().first()
        if not row:
            return None
        return {
            "run_id": row.run_id,
            "created_at": row.created_at,
            "metrics": row.metrics,
            "categories": row.categories,
            "counts": row.counts,
        }


# ------------------------------------------------------------------ Misc


def save_ontology_snapshot(key: str, payload: dict) -> None:
    with get_session() as s:
        doc = s.get(OntologyDocRow, key)
        if doc:
            doc.payload = payload
        else:
            s.add(OntologyDocRow(key=key, payload=payload))
        s.commit()


def get_ontology_snapshot(key: str) -> dict | None:
    with get_session() as s:
        doc = s.get(OntologyDocRow, key)
        return doc.payload if doc else None


# keep backend_name importable for dashboard summary
from app.database.engine import backend_name  # noqa: E402, F401