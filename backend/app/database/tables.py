"""SQLAlchemy table definitions.

The full SafetyEvent payload is stored as JSONB with indexed summary columns
for dashboard filtering/aggregation. Postgres uses JSONB; SQLite falls back to
a JSON text type transparently.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.engine import Base

# Postgres stores the full payload as JSONB; SQLite transparently falls back
# to its generic JSON text type so offline tests keep working unchanged.
PG_JSON = JSON().with_variant(JSONB, "postgresql")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


class ObservationRow(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    # Document segmentation traceability (see Observation model).
    document_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    report_segment_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    segment_index: Mapped[int | None] = mapped_column(Integer, default=None, index=False)
    narrative: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(12), default="rules")
    requested_provider: Mapped[str] = mapped_column(String(12), default="auto")
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_reason: Mapped[str] = mapped_column(Text, default="")
    event: Mapped[dict] = mapped_column(PG_JSON, default=dict)

    activity: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    task_phase: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    barrier: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    barrier_state: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    energy: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    exposure: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    location: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    potential_consequence: Mapped[str] = mapped_column(
        String(60), default="unknown", index=True
    )
    sif_classification: Mapped[str] = mapped_column(
        String(30), default="needs_review", index=True
    )
    life_saving_rules: Mapped[list] = mapped_column(PG_JSON, default=list)
    precursor_family_id: Mapped[str | None] = mapped_column(
        String(40), index=True, default=None
    )
    validation: Mapped[str] = mapped_column(String(20), default="pending")
    validation_reviewer: Mapped[str] = mapped_column(String(80), default="")
    validation_reason: Mapped[str] = mapped_column(Text, default="")
    validated_at: Mapped[str | None] = mapped_column(
        String(40), default=None
    )
    created_at: Mapped[str] = mapped_column(String(40), default=_now, index=True)

    __table_args__ = (
        Index("ix_observations_activity_time", "activity", "created_at"),
        Index("ix_observations_barrier_state_time", "barrier", "barrier_state", "created_at"),
    )


class PrecursorFamilyRow(Base):
    __tablename__ = "precursor_families"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="", index=True)
    family_type: Mapped[str] = mapped_column(String(30), default="precursor", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    recurring: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    common_barrier: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    common_barrier_state: Mapped[str] = mapped_column(
        String(30), default="unknown", index=True
    )
    common_energy: Mapped[str] = mapped_column(String(60), default="unknown", index=True)
    common_exposure: Mapped[str] = mapped_column(String(60), default="unknown")
    core_mechanism: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    context: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    recurrence: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    activities: Mapped[list] = mapped_column(PG_JSON, default=list)
    locations: Mapped[list] = mapped_column(PG_JSON, default=list)
    observation_ids: Mapped[list] = mapped_column(PG_JSON, default=list)
    hazard: Mapped[str] = mapped_column(Text, default="")
    attention_signal: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    attention_basis: Mapped[list] = mapped_column(PG_JSON, default=list)
    attention_factors: Mapped[list] = mapped_column(PG_JSON, default=list)
    sif_potential_count: Mapped[int] = mapped_column(Integer, default=0)
    recurring_threshold: Mapped[int] = mapped_column(Integer, default=2)
    grouping_evidence: Mapped[list] = mapped_column(PG_JSON, default=list)
    exclusions: Mapped[list] = mapped_column(PG_JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(40), default=_now)


class EvaluationResultRow(Base):
    __tablename__ = "evaluation_results"

    # BigInteger prevents SQLite rowid-alias autoincrement (only INTEGER
    # PRIMARY KEY is a rowid alias); Integer works on Postgres and SQLite.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=_now)
    metrics: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    categories: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    counts: Mapped[dict] = mapped_column(PG_JSON, default=dict)


class OntologyDocRow(Base):
    __tablename__ = "ontology"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(PG_JSON, default=dict)
    updated_at: Mapped[str] = mapped_column(String(40), default=_now)