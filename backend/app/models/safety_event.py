"""Canonical safety event models.

The safety-critical representation of MECHORA. LLM output enters the system
only through strict schemas; arbitrary fields are rejected. Canonical codes are
enforced with Literal types reflecting the ontology in ``data/ontology``.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Canonical code literals (mirrors data/ontology/*.json)
# ---------------------------------------------------------------------------

ACTIVITY_CODES = Literal[
    "pipeline_maintenance",
    "compressor_maintenance",
    "valve_replacement",
    "pump_maintenance",
    "tank_maintenance",
    "electrical_maintenance",
    "hot_work",
    "confined_space_entry",
    "working_at_height",
    "lifting_operations",
    "unknown",
]

TASK_PHASE_CODES = Literal[
    "pre_job", "maintenance", "repair", "operation", "installation",
    "testing", "commissioning", "cleaning", "inspection", "unknown",
]

ENERGY_CODES = Literal[
    "pressurized_gas",
    "pressurized_liquid",
    "electrical_energy",
    "flammable_atmosphere",
    "chemical_exposure",
    "thermal_energy",
    "stored_mechanical_energy",
    "gravity",
    "moving_equipment",
    "unknown",
]

BARRIER_CODES = Literal[
    "energy_isolation",
    "work_permit",
    "confined_space_procedure",
    "fall_protection",
    "hot_work_controls",
    "chemical_handling_controls",
    "machinery_guarding",
    "lifting_controls",
    "housekeeping",
    "competent_supervision",
    "unknown",
]

BARRIER_STATE_CODES = Literal[
    "verified",
    "not_verified",
    "failed",
    "partially_effective",
    "absent",
    "unknown",
]

EXPOSURE_CODES = Literal[
    "uncontrolled_gas_release",
    "uncontrolled_liquid_release",
    "electrical_shock_risk",
    "fire_or_explosion",
    "chemical_contact",
    "fall_from_height",
    "caught_in_machinery",
    "object_drop_struck_by",
    "thermal_burn",
    "confined_space_atmosphere",
    "unknown",
]

CONSEQUENCE_CODES = Literal[
    "none_identified",
    "minor_injury",
    "injury",
    "serious_injury",
    "fatality",
    "serious_injury_or_fatality",
    "asset_damage",
    "environmental_release",
    "fire",
    "explosion",
    "unknown",
]

LOCATION_CODES = Literal[
    "compressor_room",
    "pipeline_section",
    "pump_station",
    "tank_farm",
    "well_site",
    "substation",
    "workshop",
    "process_area",
    "storage_yard",
    "offshore_platform",
    "unknown",
]

LSR_CODES = Literal[
    "work_authorization",
    "gas_testing",
    "confined_space_entry",
    "working_at_height",
    "energy_isolation",
    "hot_work",
    "safe_mechanical_lifting",
    "line_of_fire",
    "bypassing_safety_controls",
    "change_management",
    "safe_operation",
    "driving_safety",
]

EVIDENCE_STATUS = Literal["grounded", "unknown", "needs_review"]

SIF_CLASS = Literal["high", "medium", "low", "needs_review"]

BARRIER_FAILURE_STATES = ("not_verified", "failed", "absent", "partially_effective")

NON_FAILURE_STATES = ("verified", "unknown")

UNKNOWN_CODE = "unknown"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    """A grounded evidence span from the original narrative."""

    model_config = ConfigDict(extra="forbid")

    span: str = ""
    sentence_index: int = -1
    source: str = "narrative"
    status: EVIDENCE_STATUS = "grounded"


# ---------------------------------------------------------------------------
# Derived assessments
# ---------------------------------------------------------------------------


class SIFAssessment(BaseModel):
    """Prototype SIF-potential assessment (decision support, not prediction)."""

    model_config = ConfigDict(extra="forbid")

    classification: SIF_CLASS = "needs_review"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    basis: Literal["explicit", "rule_inference", "needs_review"] = "rule_inference"
    reason: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    model_note: str = (
        "Prototype assessment. Decision support only; not accident prediction. "
        "Production thresholds require OIL-data calibration."
    )


class LSRMapping(BaseModel):
    """Explainable mapping to IOGP Life-Saving Rules."""

    model_config = ConfigDict(extra="forbid")

    rules: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    basis: str = ""
    evidence: list[str] = Field(default_factory=list)
    needs_review: bool = False


# ---------------------------------------------------------------------------
# Precursor family explainers
# ---------------------------------------------------------------------------


class GroupingEvidence(BaseModel):
    """Per-dimension commonality evidence (WHY GROUPED?).

    Generated from the actual per-observation comparison inside the family,
    never hardcoded: the dominant value and its coverage over members.
    """

    model_config = ConfigDict(extra="forbid")

    dimension: str = ""
    category: Literal["core_mechanism", "context"] = "core_mechanism"
    value: str = ""
    status: Literal["same", "mixed", "distinct", "unknown"] = "same"
    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    note: str = ""


class ExclusionEntry(BaseModel):
    """WHY NOT GROUPED: a structurally-similar family kept separate."""

    model_config = ConfigDict(extra="forbid")

    other_family_id: str = ""
    other_family_name: str = ""
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    differing_dimensions: list[str] = Field(default_factory=list)
    dimension_values: list[dict[str, str]] = Field(default_factory=list)
    dimension_comparisons: list[dict[str, str]] = Field(default_factory=list)
    basis: str = ""


# ---------------------------------------------------------------------------
# Precursor signature
# ---------------------------------------------------------------------------


class PrecursorSignature(BaseModel):
    """Machine-comparable structural signature (PRD section 13)."""

    model_config = ConfigDict(extra="forbid")

    # Core mechanism dimensions (authoritative for mechanism grouping)
    energy: ENERGY_CODES = "unknown"
    barrier: BARRIER_CODES = "unknown"
    barrier_state: BARRIER_STATE_CODES = "unknown"
    exposure: EXPOSURE_CODES = "unknown"

    # Context dimensions (context variation across activities)
    task_phase: TASK_PHASE_CODES = "unknown"
    activity: ACTIVITY_CODES = "unknown"
    potential_consequence: CONSEQUENCE_CODES = "unknown"


# ---------------------------------------------------------------------------
# Strict LLM extraction schema (the only shape the AI may emit)
# ---------------------------------------------------------------------------


class LLMExtraction(BaseModel):
    """Strict structured output of the extraction stage.

    The LLM may only emit these fields with canonical codes. The pipeline
    independently validates, normalizes and (for barrier state) re-derives
    values, so LLM drift cannot silently enter the core model.
    """

    model_config = ConfigDict(extra="forbid")

    activity: ACTIVITY_CODES = "unknown"
    task_phase: TASK_PHASE_CODES = "unknown"
    hazard: str = Field(default="unknown", max_length=300)
    energy: ENERGY_CODES = "unknown"
    unsafe_action: str = Field(default="unknown", max_length=500)
    unsafe_condition: str = Field(default="unknown", max_length=500)
    barrier: BARRIER_CODES = "unknown"
    barrier_state: BARRIER_STATE_CODES = "unknown"
    exposure: EXPOSURE_CODES = "unknown"
    actual_consequence: str = Field(default="unknown", max_length=300)
    potential_consequence: CONSEQUENCE_CODES = "unknown"
    location: LOCATION_CODES = "unknown"
    life_saving_rules: list[LSR_CODES] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list, max_length=40)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return round(max(0.0, min(1.0, v)), 4)


# ---------------------------------------------------------------------------
# Canonical safety event
# ---------------------------------------------------------------------------


class SafetyEvent(BaseModel):
    """The canonical, validated safety event (PRD sections 5 & 12)."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = ""
    narrative: str = Field(default="", max_length=20000)

    activity: ACTIVITY_CODES = "unknown"
    task_phase: TASK_PHASE_CODES = "unknown"

    hazard: str = "unknown"
    energy: ENERGY_CODES = "unknown"

    unsafe_action: str = "unknown"
    unsafe_condition: str = "unknown"

    barrier: BARRIER_CODES = "unknown"
    barrier_state: BARRIER_STATE_CODES = "unknown"

    exposure: EXPOSURE_CODES = "unknown"

    actual_consequence: CONSEQUENCE_CODES = "unknown"
    potential_consequence: CONSEQUENCE_CODES = "unknown"
    potential_consequence_basis: Literal[
        "unknown", "explicit", "model_inference"
    ] = "unknown"

    location: LOCATION_CODES = "unknown"

    life_saving_rules: list[LSR_CODES] = Field(default_factory=list)

    evidence: list[Evidence] = Field(default_factory=list)

    field_evidence: dict[str, str] = Field(default_factory=dict)

    # Per-field provenance: "explicit" (verbatim span supports the value),
    # "inferred" (rule-derived value with no direct span) or "unknown".
    # Inferred values must never be displayed as if directly extracted.
    field_basis: dict[str, str] = Field(default_factory=dict)

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    evidence_status: EVIDENCE_STATUS = "grounded"

    # Unknown / needs-review handling (PRIORITY: unknown over invented value).
    missing_fields: list[str] = Field(default_factory=list)
    needs_review: bool = False

    precursor_signature: PrecursorSignature = Field(default_factory=PrecursorSignature)

    sif: SIFAssessment = Field(default_factory=SIFAssessment)
    lsr_mapping: LSRMapping = Field(default_factory=LSRMapping)


# ---------------------------------------------------------------------------
# Persisted observation document
# ---------------------------------------------------------------------------


class Observation(BaseModel):
    """A persisted safety observation (analysis plus metadata)."""

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    report_id: str = ""
    narrative: str = ""
    provider: Literal["llm", "rules", "hybrid"] = "rules"
    # Extraction provenance (what was asked for, whether a graceful fallback
    # happened, and why) so every surfaced finding is auditable end-to-end.
    requested_provider: str = "auto"
    fallback_used: bool = False
    fallback_reason: str = ""
    event: SafetyEvent = Field(default_factory=SafetyEvent)
    precursor_family_id: str | None = None
    validation: Literal["pending", "validated", "rejected"] = "pending"
    # HSE human-in-the-loop audit trail. Empty until an HSE reviewer acts.
    validation_reviewer: str = ""
    validation_reason: str = ""
    validated_at: str | None = None
    created_at: str = Field(
        default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Precursor family
# ---------------------------------------------------------------------------


FAMILY_TYPE_CODES = Literal["precursor", "controlled", "needs_review"]


class PrecursorFamily(BaseModel):
    """A group of observations sharing a structural precursor mechanism."""

    model_config = ConfigDict(extra="forbid")

    id: str = ""
    name: str = ""
    family_type: FAMILY_TYPE_CODES = "precursor"
    description: str = ""
    observation_ids: list[str] = Field(default_factory=list)

    # Core Mechanism
    common_barrier: BARRIER_CODES = "unknown"
    common_barrier_state: BARRIER_STATE_CODES = "unknown"
    common_energy: ENERGY_CODES = "unknown"
    common_exposure: EXPOSURE_CODES = "unknown"
    core_mechanism: dict[str, str] = Field(default_factory=dict)

    # Context & Scope
    context: dict[str, Any] = Field(default_factory=dict)
    activities: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    hazard: str = ""

    # Recurrence Intelligence
    recurrence: dict[str, Any] = Field(default_factory=dict)
    recurring: bool = False
    recurring_threshold: int = 2
    sif_potential_count: int = 0
    why_it_matters: str = ""

    # Attention & Explainability
    attention_signal: float = Field(default=0.0, ge=0.0, le=100.0)
    attention_basis: list[str] = Field(default_factory=list)
    attention_factors: list[dict[str, Any]] = Field(default_factory=list)
    grouping_evidence: list[GroupingEvidence] = Field(default_factory=list)
    exclusions: list[ExclusionEntry] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Ontology concept (read-only view used by API / frontend)
# ---------------------------------------------------------------------------


class OntologyConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    category: str
    description: str = ""
    synonyms: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)