"""CAPA (Corrective And Preventive Action) entities and status codes.

A CAPA is a corrective/preventative improvement targeted at a **barrier**
(``Observation -> Barrier -> CAPA``, per the effectiveness PRD). The primary
relationship is barrier->CAPA, so future observations with different wording can
still be evaluated against the same safety barrier.

``effectiveness_*`` are DERIVED from persisted evidence (baseline barrier-state
observations BEFORE the CAPA vs. barrier-state observations after closure). They
are never fabricated, guessed or scored arbitrarily.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CAPA_STATUS_CODES = Literal[
    "open",
    "in_progress",
    "closed",
    "cancelled",
    "draft",
]

EFFECTIVENESS_STATUS_CODES = Literal[
    "improvement_observed",
    "recurrence_detected",
    "insufficient_evidence",
    "under_observation",
]

EFFECTIVENESS_STATUS_LABELS: dict[str, str] = {
    "improvement_observed": "Evidence of Improvement",
    "recurrence_detected": "Recurrence Detected",
    "insufficient_evidence": "Insufficient Evidence",
    "under_observation": "Under Observation",
}

CAPA_STATUS_LABELS: dict[str, str] = {
    "open": "Open",
    "in_progress": "In Progress",
    "closed": "Closed",
    "cancelled": "Cancelled",
    "draft": "Draft",
}

BARRIER_FAILURE_STATES = ("not_verified", "failed", "absent", "partially_effective")


def effectiveness_status_label(status: str) -> str:
    return EFFECTIVENESS_STATUS_LABELS.get(status, status.replace("_", " ").title())


def capa_status_label(status: str) -> str:
    return CAPA_STATUS_LABELS.get(status, status.replace("_", " ").title())


class BaselineSnapshot(BaseModel):
    """Baseline barrier-state evidence BEFORE the CAPA (reproducible)."""

    model_config = ConfigDict(extra="forbid")

    barrier: str = "unknown"
    barrier_state: str = "unknown"
    energy: str = "unknown"
    exposure: str = "unknown"
    location: str = "unknown"
    window_days: int = 90
    from_iso: str = ""
    to_iso: str = ""
    failure_count: int = 0
    sif_potential_count: int = 0
    affected_sites: int = 0
    observation_ids: list[str] = Field(default_factory=list)


class PostCAPASnapshot(BaseModel):
    """Post-CAPA barrier-state evidence AFTER closure (reproducible).

    ``observation_ids`` lists EVERY barrier-state observation counted inside the
    post-closure window (recurrences plus verified/unknown controls) so the UI
    can show the exact evidence that led to the effectiveness verdict.
    """

    model_config = ConfigDict(extra="forbid")

    barrier: str = "unknown"
    barrier_state: str = "unknown"
    window_days: int = 90
    from_iso: str = ""
    to_iso: str = ""
    recurrence_count: int = 0
    recurrence_observation_ids: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)


class CAPA(BaseModel):
    """A persisted CAPA targeted at a barrier.

    Flat surface mirroring ``CAPARow`` exactly so the repos round-trip is
    lossless: ``baseline`` / ``post_capa`` are typed evidence snapshots,
    ``effectiveness_*`` are flat DERIVED columns, ``evidence_observation_ids``
    back-reference persisted observations.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    report_id: str = ""
    title: str = ""
    description: str = ""
    linked_barrier_id: str = "unknown"
    location: str = "unknown"
    site: str = "unknown"
    status: CAPA_STATUS_CODES = "open"
    created_at: str = ""
    closed_at: str | None = None
    baseline: BaselineSnapshot = Field(default_factory=BaselineSnapshot)
    post_capa: PostCAPASnapshot = Field(default_factory=PostCAPASnapshot)
    effectiveness_status: EFFECTIVENESS_STATUS_CODES = "insufficient_evidence"
    effectiveness_basis: dict = Field(default_factory=dict)
    evidence_observation_ids: list[str] = Field(default_factory=list)