"""Persistence repository layer.

All database access for the application. Family (re)assignment happens in a
single transaction: observations are recomputed structurally and family rows
are rebuilt, keeping ``report_id``/``observation_id`` references consistent.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.engine import get_session
from app.database.tables import (
    AuditEntryRow,
    CAPARow,
    EvaluationResultRow,
    ObservationRow,
    OntologyDocRow,
    PrecursorFamilyRow,
)
from app.models.capa import CAPA
from app.models.safety_event import Observation, PrecursorFamily
from app.services.precursor.engine import PrecursorEngine

logger = logging.getLogger("mechora.repos")


def new_observation_id(report_id: str | None = None) -> str:
    """Canonical observation id: ``OBS-<REPORT_ID>`` — deterministic (the same
    report always yields the same id) and uniform for every observation, so a
    re-analyzed report updates its record instead of creating a duplicate.
    Falls back to a random ``OBS-`` id when the report id is empty/quoted.
    """
    raw = (report_id or "").strip()[:36].upper()
    slug = re.sub(r"[^A-Z0-9]+", "-", raw).strip("-")
    if slug:
        return f"OBS-{slug}"[:40]
    return "OBS-" + uuid.uuid4().hex[:10].upper()


def _obs_to_row(obs: Observation) -> ObservationRow:
    ev = obs.event
    return ObservationRow(
        id=obs.id,
        report_id=obs.report_id,
        document_id=obs.document_id,
        report_segment_id=obs.report_segment_id,
        segment_index=obs.segment_index,
        narrative=obs.narrative,
        provider=obs.provider,
        requested_provider=obs.requested_provider,
        fallback_used=obs.fallback_used,
        fallback_reason=obs.fallback_reason,
        report_type=obs.report_type,
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
        validation_reviewer=obs.validation_reviewer,
        validation_reason=obs.validation_reason,
        validated_at=obs.validated_at,
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
        requested_provider=getattr(row, "requested_provider", "auto") or "auto",
        fallback_used=bool(getattr(row, "fallback_used", False)),
        fallback_reason=getattr(row, "fallback_reason", "") or "",
        event=SafetyEvent.model_validate(event),
        precursor_family_id=row.precursor_family_id,
        validation=row.validation,
        validation_reviewer=getattr(row, "validation_reviewer", "") or "",
        validation_reason=getattr(row, "validation_reason", "") or "",
        validated_at=getattr(row, "validated_at", None),
        document_id=getattr(row, "document_id", "") or "",
        report_segment_id=getattr(row, "report_segment_id", "") or "",
        segment_index=getattr(row, "segment_index", None),
        report_type=getattr(row, "report_type", "unknown") or "unknown",
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
    created_before: str | None = None
    created_after: str | None = None
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


def _recompute_effectiveness_after_evidence_change() -> None:
    """Re-derive every CAPA's effectiveness from persisted observations.

    Effectiveness snapshots are precomputed and stored on the row, so any
    observation write (create/delete) can otherwise leave a closed CAPA serving
    stale recurrence evidence. Recomputed lazily here (import kept inline to
    avoid a circular import: ``app.services.capa.effectiveness`` imports repos).
    """
    from app.services.capa.effectiveness import recompute_all_effectiveness

    recompute_all_effectiveness()


def create_observation(obs: Observation, recompute: bool = True) -> Observation:
    if not obs.id:
        obs.id = new_observation_id(obs.report_id)
    with get_session() as s:
        existing = s.get(ObservationRow, obs.id)
        if existing is None:
            existing = s.query(ObservationRow).filter_by(
                report_id=obs.report_id
            ).first()
        row = _obs_to_row(obs)
        if existing is not None:
            row.id = existing.id
            row.report_id = existing.report_id
            stored_id = s.merge(row).id
        else:
            s.add(row)
            stored_id = row.id
        s.commit()
    if recompute:
        recompute_families()
        _recompute_effectiveness_after_evidence_change()
    with get_session() as s:
        row = s.get(ObservationRow, stored_id)
        return _row_to_obs(row) if row else obs


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
                obs.id = new_observation_id(obs.report_id)
            s.add(_obs_to_row(obs))
        s.commit()
    recompute_families()
    _recompute_effectiveness_after_evidence_change()
    return len(observations)


def get_observation(obs_id: str) -> Observation | None:
    with get_session() as s:
        row = s.get(ObservationRow, obs_id)
        return _row_to_obs(row) if row else None


def get_observation_by_report_id(report_id: str) -> Observation | None:
    with get_session() as s:
        row = s.query(ObservationRow).filter_by(report_id=report_id).first()
        return _row_to_obs(row) if row else None


def delete_observation(obs_id: str) -> bool:
    """Delete an observation and rebuild families so family membership and the
    ``precursor_family_id`` back-reference stay consistent. CAPA effectiveness
    is recomputed too so a removed observation can never leave stale
    recurrence evidence persisted on a closed CAPA."""
    with get_session() as s:
        row = s.get(ObservationRow, obs_id)
        if row is None:
            return False
        s.delete(row)
        s.commit()
    recompute_families()
    _recompute_effectiveness_after_evidence_change()
    return True


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


def update_validation(
    obs_id: str,
    status: str,
    reviewer: str = "",
    reason: str = "",
) -> Observation | None:
    with get_session() as s:
        row = s.get(ObservationRow, obs_id)
        if not row:
            return None
        row.validation = status
        row.validation_reviewer = (reviewer or "").strip()[:80]
        row.validation_reason = (reason or "").strip()[:2000]
        row.validated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
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


def list_families(recurring_only: bool = False, limit: int = 200,
                  include_controls: bool = False) -> list[PrecursorFamily]:
    """List precursor families.

    Verified/compliance (``family_type == "controlled"``) groups are NOT
    precursor families and are excluded by default — they remain available as
    hard-negative control groups for validation via ``get_family()`` or
    ``include_controls=True``.
    """
    with get_session() as s:
        stmt = select(PrecursorFamilyRow).order_by(
            PrecursorFamilyRow.attention_signal.desc()
        )
        if not include_controls:
            stmt = stmt.where(PrecursorFamilyRow.family_type != "controlled")
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
            s.execute(
                select(func.count())
                .select_from(PrecursorFamilyRow)
                .where(PrecursorFamilyRow.family_type != "controlled")
            ).scalar_one()
        )
        recurring = int(
            s.execute(
                select(func.count())
                .select_from(PrecursorFamilyRow)
                .where(
                    (PrecursorFamilyRow.family_type != "controlled")
                    & PrecursorFamilyRow.recurring.is_(True)
                )
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


# -------------------------------------------------------------------- CAPA


def new_capa_id(report_id: str | None = None) -> str:
    """Deterministic CAPA id: ``CAPA-<REPORT_ID>`` (same id for the same report,
    mirroring ``new_observation_id``). Falls back to a random ``CAPA-`` id for
    empty/unassigned report ids so the intake path never collides."""
    raw = (report_id or "").strip().upper()[:36]
    slug = re.sub(r"[^A-Z0-9]+", "-", raw).strip("-")
    if slug:
        return f"CAPA-{slug}"[:40]
    return "CAPA-" + uuid.uuid4().hex[:10].upper()


def _build_capa_row(capa: CAPA) -> CAPARow:
    return CAPARow(
        id=capa.id,
        report_id=capa.report_id,
        title=capa.title,
        description=capa.description,
        linked_barrier_id=capa.linked_barrier_id,
        location=capa.location,
        site=capa.site,
        status=capa.status,
        created_at=capa.created_at or _now(),
        closed_at=capa.closed_at,
        baseline=capa.baseline.model_dump(mode="json") if capa.baseline else dict,
        post_capa=capa.post_capa.model_dump(mode="json") if capa.post_capa else dict,
        effectiveness_status=capa.effectiveness_status,
        effectiveness_basis=capa.effectiveness_basis,
        evidence_observation_ids=capa.evidence_observation_ids,
    )


def _row_to_capa(row: CAPARow) -> CAPA:
    return CAPA(
        id=row.id,
        report_id=row.report_id,
        title=row.title,
        description=row.description,
        linked_barrier_id=row.linked_barrier_id,
        location=row.location,
        site=row.site,
        status=row.status,
        created_at=row.created_at,
        closed_at=row.closed_at,
        baseline=row.baseline,
        post_capa=row.post_capa,
        effectiveness_status=row.effectiveness_status,
        effectiveness_basis=row.effectiveness_basis,
        evidence_observation_ids=row.evidence_observation_ids,
    )


def create_capa(capa: CAPA, recompute: bool = True) -> CAPA:
    if not capa.id:
        capa.id = new_capa_id(capa.report_id)
    # The report_id column is unique; a CAPA without a source report cannot
    # reuse the empty string or it would collide with a sibling record. Its own
    # generated id is a stable, unique back-reference in that case.
    if not capa.report_id.strip():
        capa.report_id = capa.id
    with get_session() as s:
        existing = s.get(CAPARow, capa.id)
        if existing is None:
            existing = s.query(CAPARow).filter_by(report_id=capa.report_id).first()
        if existing is not None:
            keep_id = existing.id
            replace = _build_capa_row(capa)
            replace.id = keep_id
            replace.report_id = existing.report_id
            s.merge(replace)
            stored_id = keep_id
        else:
            s.add(_build_capa_row(capa))
            stored_id = capa.id
        s.commit()
    if recompute:
        from app.services.capa.effectiveness import recompute_all_effectiveness

        recompute_all_effectiveness()
    with get_session() as s:
        row = s.get(CAPARow, stored_id)
    return _row_to_capa(row) if row else capa


def get_capa(capa_id: str) -> CAPA | None:
    with get_session() as s:
        row = s.get(CAPARow, capa_id)
        return _row_to_capa(row) if row else None


def get_capa_by_report_id(report_id: str) -> CAPA | None:
    with get_session() as s:
        row = s.query(CAPARow).filter_by(report_id=report_id).first()
        return _row_to_capa(row) if row else None


def list_capas(
    filters: ObservationFilters | None = None,
    status: str | None = None,
    barrier: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CAPA]:
    with get_session() as s:
        stmt = select(CAPARow).order_by(CAPARow.created_at.desc())
        if status:
            stmt = stmt.where(CAPARow.status == status)
        if barrier:
            stmt = stmt.where(CAPARow.linked_barrier_id == barrier)
        rows = s.execute(stmt.limit(limit).offset(offset)).scalars().all()
        return [_row_to_capa(r) for r in rows]


def count_capas(status: str | None = None, barrier: str | None = None) -> int:
    with get_session() as s:
        stmt = select(func.count()).select_from(CAPARow)
        if status:
            stmt = stmt.where(CAPARow.status == status)
        if barrier:
            stmt = stmt.where(CAPARow.linked_barrier_id == barrier)
        return int(s.execute(stmt).scalar_one())


def delete_capa(capa_id: str) -> bool:
    with get_session() as s:
        row = s.get(CAPARow, capa_id)
        if row is None:
            return False
        s.delete(row)
        s.commit()
    return True


def update_capa_status(
    capa_id: str, status: str, closed_at: str | None = None
) -> CAPA | None:
    with get_session() as s:
        row = s.get(CAPARow, capa_id)
        if row is None:
            return None
        row.status = status
        if closed_at:
            row.closed_at = closed_at
        s.commit()
    # Closing opens the post-CAPA evidence window; recompute the derived
    # effectiveness immediately so the API never serves a stale status.
    if status == "closed":
        from app.services.capa.effectiveness import recompute_capa_effectiveness

        with get_session() as s:
            row = s.get(CAPARow, capa_id)
        if row is not None:
            resolved = recompute_capa_effectiveness(_row_to_capa(row))
            if resolved is not None:
                return resolved
    with get_session() as s:
        row = s.get(CAPARow, capa_id)
        return _row_to_capa(row) if row else None


def update_capa_effectiveness(
    capa_id: str,
    effectiveness_status: str,
    effectiveness_basis: dict | None = None,
    baseline: dict | None = None,
    post_capa: dict | None = None,
    evidence_observation_ids: list[str] | None = None,
) -> CAPA | None:
    """Persist the DERIVED effectiveness result computed by the effectiveness
    engine (never fabrication). Keeps the DERIVED fields on the row so the
    dashboard/API can serve precomputed values cheaply."""
    with get_session() as s:
        row = s.get(CAPARow, capa_id)
        if row is None:
            return None
        row.effectiveness_status = effectiveness_status
        if effectiveness_basis is not None:
            row.effectiveness_basis = effectiveness_basis
        if baseline is not None:
            row.baseline = baseline
        if post_capa is not None:
            row.post_capa = post_capa
        if evidence_observation_ids is not None:
            row.evidence_observation_ids = evidence_observation_ids
        s.commit()
        s.refresh(row)
    return _row_to_capa(row)


# ------------------------------------------------------------------ Audit log


def audit_log(action: str, actor: str = "system", detail: str = "") -> None:
    """Append one lightweight entry to the internal audit trail.

    ``actor`` is an identity (email or role), ``action`` is a short enum-like
    token (e.g. ``auth.login_success``, ``observation.validation``) and
    ``detail`` is a short human-readable description. Failures here must never
    break the request that triggered the audit, so exceptions are logged.
    """
    try:
        with get_session() as s:
            s.add(
                AuditEntryRow(
                    actor=(actor or "system")[:120],
                    action=(action or "")[:60],
                    detail=(detail or "")[:2000],
                )
            )
            s.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit_log failed for %s: %s", action, exc)


def audit_entries(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    with get_session() as s:
        rows = s.execute(
            select(AuditEntryRow)
            .order_by(AuditEntryRow.id.desc())
            .limit(max(1, min(limit, 500)))
            .offset(max(0, offset))
        ).scalars().all()
        return [
            {
                "id": r.id,
                "actor": r.actor,
                "action": r.action,
                "detail": r.detail,
                "created_at": r.created_at,
            }
            for r in rows
        ]


def count_audit_entries() -> int:
    with get_session() as s:
        return int(
            s.execute(select(func.count()).select_from(AuditEntryRow)).scalar_one()
        )


# keep backend_name importable for dashboard summary
from app.database.engine import backend_name  # noqa: E402, F401