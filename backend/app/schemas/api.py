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
    provider: str | None = Field(
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
    report_type: str = "ua_uc"


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
    report_type: str = "ua_uc"
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