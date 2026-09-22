"""API request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.safety_event import SafetyEvent, PrecursorFamily

ValidationStatus = Literal["pending", "validated", "rejected"]


class AnalyzeRequest(BaseModel):
    report_id: str = Field(
        default="REPORT-UNASSIGNED",
        description="External report identifier; may be churned/placeholder.",
    )
    narrative: str = Field(
        min_length=8, max_length=3000,
        description="Untrusted HSE narrative text to analyze.",
    )
    provider: Literal["rules", "llm", "auto"] | None = Field(
        default=None, description="rules | llm | auto (default from settings)."
    )
    report_type: Literal["ua_uc", "near_miss", "incident", "unknown"] = Field(
        default="unknown",
        description="Reporter-selected classification at intake (metadata only).",
    )


class AnalyzeResponse(BaseModel):
    id: str
    report_id: str
    provider: str
    resolved_provider: str = ""
    requested_provider: str = "auto"
    fallback_used: bool = False
    fallback_reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    event: Any
    precursor_family_id: str | None = None
    document_id: str = ""
    report_segment_id: str = ""
    segment_index: int | None = None
    report_type: str = "unknown"


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    narrative: str
    provider: str
    resolved_provider: str = ""
    requested_provider: str = "auto"
    fallback_used: bool = False
    fallback_reason: str = ""
    event: SafetyEvent
    precursor_family_id: str | None = None
    validation: ValidationStatus = "pending"
    validation_reviewer: str = ""
    validation_reason: str = ""
    validated_at: str | None = None
    document_id: str = ""
    report_segment_id: str = ""
    segment_index: int | None = None
    report_type: str = "unknown"
    created_at: str


class ObservationList(BaseModel):
    total: int
    observations: list[ObservationOut]


# ---------------------------------------------------------------------------
# Document extraction & segmentation
# ---------------------------------------------------------------------------


class DocumentSegment(BaseModel):
    """One classified block of an extracted document.

    ``kind`` is ``report`` (analyzed, persisted separately) or ``non_report``
    (headings, metadata, "Expected Test Signals", page furniture — excluded
    from analysis, evidence and traceability).
    """

    index: int
    kind: str
    heading: str = ""
    text: str = ""
    character_count: int = 0


class ExtractionResponse(BaseModel):
    filename: str
    file_type: str
    text: str
    character_count: int
    report_count: int
    segments: list[DocumentSegment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SegmentAnalysis(BaseModel):
    report_segment_id: str
    segment_index: int
    heading: str = ""
    analysis: AnalyzeResponse | None = None
    error: str = ""


class DocumentAnalysisResponse(BaseModel):
    document_id: str
    report_count: int
    analyses: list[SegmentAnalysis] = Field(default_factory=list)
    observations_created: int = 0
    warnings: list[str] = Field(default_factory=list)


class FamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    observation_ids: list[str]
    common_barrier: str
    common_barrier_state: str
    common_energy: str
    common_exposure: str
    activities: list[str]
    locations: list[str]
    hazard: str
    family_type: str = "precursor"
    core_mechanism: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    recurrence: dict = Field(default_factory=dict)
    why_it_matters: str = ""
    attention_signal: float
    attention_basis: list[str]
    attention_factors: list[dict] = Field(default_factory=list)
    sif_potential_count: int
    recurring: bool
    recurring_threshold: int = 2
    grouping_evidence: list[dict] = Field(default_factory=list)
    exclusions: list[dict] = Field(default_factory=list)
    created_at: str


class FamilyList(BaseModel):
    total: int
    recurring: int
    families: list[FamilyOut]


class ValidationUpdate(BaseModel):
    status: ValidationStatus
    reviewer: str | None = Field(
        default=None, description="HSE reviewer identity for the audit trail."
    )
    reason: str | None = Field(
        default=None, max_length=2000,
        description="Optional rationale recorded for the HSE audit trail.",
    )


class OntologyConcept(BaseModel):
    code: str
    synonyms: list[str]


class OntologyCategory(BaseModel):
    category: str
    concepts: list[OntologyConcept]


class DashboardOut(BaseModel):
    total_observations: int
    sif_potential_observations: int
    precursor_families: int
    recurring_precursor_families: int
    recurring_barrier_failures: int
    locations_affected: int
    activities_affected: int
    backend: str


class EvaluationOut(BaseModel):
    run_id: str
    created_at: str
    metrics: dict[str, Any]
    categories: dict[str, Any]
    counts: dict[str, Any]


class CapaCreate(BaseModel):
    """Intake for creating a CAPA.

    ``linked_barrier_id`` is required: a CAPA is always targeted at one
    persisted safety barrier, because the effectiveness engine recomputes its
    evidence windows against exactly that barrier (all deterministic, derived
    from persisted observations -- never synthetic).
    """

    model_config = ConfigDict(extra="forbid")

    report_id: str = ""
    title: str = Field(min_length=4, max_length=160)
    description: str = Field(default="", max_length=4000)
    linked_barrier_id: str = Field(default="unknown", max_length=60)
    location: str = Field(default="unknown", max_length=80)
    site: str = Field(default="unknown", max_length=80)
    status: str = "open"
    window_days: int = Field(default=90, ge=7, le=365)
    created_at: str = ""


class CapaStatusUpdate(BaseModel):
    """Status transition for a CAPA (open -> in_progress -> closed)."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=2, max_length=20)
    closed_at: str | None = None


class CapaEffectivenessUpdate(BaseModel):
    """Optional manual override of a CAPA's derived effectiveness.

    Note the app's contract: effectiveness is normally DERIVED deterministically
    by ``app.services.capa.effectiveness`` from persisted evidence. This schema
    exists only to record a human-reviewed verdict (basis) when an operator
    wants to supersede the machine derivation.
    """

    model_config = ConfigDict(extra="forbid")

    effectiveness_status: str = Field(min_length=2, max_length=40)
    effectiveness_basis: dict | None = None
    evidence_observation_ids: list[str] = Field(default_factory=list)


class CapaOut(BaseModel):
    """Flat CAPA response, mirroring ``app.models.capa.CAPA`` exactly so the
    API object-model round trip is lossless. Derived fields are served
    precomputed (recomputed on create/close, persisted via repos)."""

    id: str
    report_id: str
    title: str
    description: str
    linked_barrier_id: str
    location: str
    site: str
    status: str
    created_at: str
    closed_at: str | None = None
    baseline: dict[str, Any] | None = None
    post_capa: dict[str, Any] | None = None
    effectiveness_status: str = "insufficient_evidence"
    effectiveness_basis: dict[str, Any] | None = None
    evidence_observation_ids: list[str] = Field(default_factory=list)


class CapaList(BaseModel):
    capas: list[CapaOut]
    total: int
    limit: int
    offset: int