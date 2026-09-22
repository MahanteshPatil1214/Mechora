"""Regression: Gemini extraction quality for REQUIRED BARRIER inference.

The confined-space entry report describes the required control through its
failures ("required entry controls had not been verified", ventilation was
inadequate, atmosphere not confirmed safe) instead of naming a barrier code.
The extraction instructions must teach Gemini to map that described control to
the EXISTING canonical barrier ``confined_space_procedure`` while:

* barrier stays a NARRATIVE-driven concept (never reverse-engineered from the
  Life-Saving Rules: narrative evidence -> required control -> canonical
  barrier -> barrier state -> LSR),
* potential consequence and SIF classification stay deterministic/authoritative,
* evidence stays verbatim from the narrative,
* validation is not weakened and ``unknown`` remains honest when no evidence
  exists for any canonical barrier.

The Gemini client is stubbed; no live API call is made here.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import get_args

from app.config import get_settings
from app.models.safety_event import (
    BARRIER_CODES,
    CONSEQUENCE_CODES,
    EXPOSURE_CODES,
)
from app.services.extraction.llm_extractor import (
    _SYSTEM_INSTRUCTION,
    _build_prompt,
)
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

CONSEQUENCE_VALUES = frozenset(get_args(CONSEQUENCE_CODES))
EXPOSURE_VALUES = frozenset(get_args(EXPOSURE_CODES))
BARRIER_VALUES = frozenset(get_args(BARRIER_CODES))

OBSERVATION = (
    "Before entering the vessel for internal inspection, the crew proceeded "
    "without confirming that the atmosphere had been checked or that the space "
    "was safe for entry. The worker entered the vessel while ventilation was "
    "inadequate, and the required entry controls had not been verified."
)

# Fixed Gemini output after the instruction update: the described entry control
# maps to the existing canonical barrier. potential_consequence/SIF must be
# derived by the deterministic layer regardless.
GEMINI_PAYLOAD = {
    "activity": "confined_space_entry",
    "task_phase": "inspection",
    "hazard": "unguarded confined space with possibly flammable atmosphere",
    "energy": "flammable_atmosphere",
    "unsafe_action": "entered the vessel without confirming the atmosphere was safe",
    "unsafe_condition": "required entry controls had not been verified",
    "barrier": "confined_space_procedure",
    "barrier_state": "not_verified",
    "exposure": "confined_space_atmosphere",
    "actual_consequence": "unknown",
    "potential_consequence": "serious_injury_or_fatality",
    "location": "unknown",
    "life_saving_rules": ["confined_space_entry", "gas_testing"],
    "evidence": ["required entry controls had not been verified"],
    "confidence": 0.9,
}


def _pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(get_ontology(), get_settings())


def _stub_pipeline(payload: dict, calls: dict):
    """Pipeline whose LLM path returns ``payload`` JSON via a fake
    google.genai-style client (records the prompt/instruction in ``calls``)."""
    pipeline = _pipeline()

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls["contents"] = contents
            calls["system_instruction"] = config.system_instruction
            return SimpleNamespace(text=json.dumps(payload))

    class _FakeClient:
        def __init__(self, api_key=None):
            self.models = _FakeModels()

    pipeline.llm_extractor._client = _FakeClient()
    return pipeline


def test_confined_space_entry_barrier_mapped_and_provider_is_gemini():
    calls: dict = {}
    result = _stub_pipeline(GEMINI_PAYLOAD, calls).analyze(
        "CONF-ENTRY-1", OBSERVATION, provider="llm"
    )
    assert calls["contents"], "Gemini client must actually be invoked"
    assert result.provider == "llm"
    assert result.fallback_used is False
    assert result.warnings == []

    ev = result.event
    assert ev.activity == "confined_space_entry"
    assert ev.task_phase == "inspection"
    assert ev.energy == "flammable_atmosphere"
    assert ev.exposure == "confined_space_atmosphere"
    assert ev.barrier == "confined_space_procedure"
    assert ev.barrier_state == "not_verified"
    assert ev.missing_fields == []

    # Barrier evidence is narrative-driven: the deterministic grounder must
    # attach the verbatim entry-control span, and the model's evidence list
    # (exactly the phrase the task requires) must survive as grounded evidence.
    barrier_evidence = ev.field_evidence.get("barrier", "")
    assert "entry controls" in barrier_evidence
    assert all(
        span in OBSERVATION for span in ev.field_evidence.values()
    ), f"field evidence not verbatim: {ev.field_evidence!r}"
    assert any(
        item.span == "required entry controls had not been verified"
        for item in ev.evidence
    )
    assert all(item.status == "grounded" for item in ev.evidence)

    # Consequence contract (deterministic despite the downstream values).
    assert ev.potential_consequence in CONSEQUENCE_VALUES
    assert ev.potential_consequence not in EXPOSURE_VALUES
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.potential_consequence_basis == "model_inference"
    assert ev.sif.classification == "high"
    assert ev.sif.basis == "rule_inference"


def test_barrier_not_derived_from_life_saving_rule():
    """A proposed Life-Saving Rule must never manufacture a barrier. With no
    entry-control evidence in the narrative, barrier stays unknown even when
    the model lists the confined_space_entry rule."""
    narrative = "The crew continued work through the shift with no other details."
    payload = {
        "activity": "unknown",
        "task_phase": "maintenance",
        "hazard": "unknown",
        "energy": "unknown",
        "barrier": "unknown",
        "barrier_state": "unknown",
        "exposure": "unknown",
        "actual_consequence": "unknown",
        "potential_consequence": "unknown",
        "location": "unknown",
        "life_saving_rules": ["confined_space_entry"],
        "evidence": [],
        "confidence": 0.5,
    }
    result = _stub_pipeline(payload, {}).analyze(
        "CONF-ENTRY-2", narrative, provider="llm"
    )
    assert result.provider == "llm"
    assert result.event.barrier == "unknown"
    assert result.event.barrier_state == "unknown"


def test_extraction_instructions_teach_contextual_barrier_mapping():
    """The instructions must teach that barrier is the REQUIRED control,
    mapped from narrative evidence (including failed/missing controls), and
    never reverse-engineered from a Life-Saving Rule."""
    instruction = _SYSTEM_INSTRUCTION
    assert "confined_space_procedure" in instruction
    assert "entry controls" in instruction
    assert "space was safe for entry" in instruction
    assert "MISSING" in instruction
    assert "UNVERIFIED" in instruction
    assert "FAILED" in instruction
    assert "INEFFECTIVE" in instruction
    assert "Never derive the barrier from the Life-Saving Rules" in instruction
    assert (
        "required control -> canonical barrier -> barrier state -> "
        "life_saving_rules" in "\n".join(instruction.splitlines())
    )
    assert "required entry controls had not been verified" in instruction

    extractor = _stub_pipeline(GEMINI_PAYLOAD, {}).llm_extractor
    prompt = _build_prompt(extractor._vocab(get_ontology()))
    assert "confined_space_procedure" in prompt
    assert "required entry controls had not been verified" in prompt
    assert "Never derive the barrier from the Life-Saving Rules" in prompt


def test_deterministic_layers_override_llm_barrier_state_and_consequence():
    """barrier_state and potential_consequence are re-derived by the
    deterministic safety engine even when Gemini proposes wrong values."""
    poisoned = dict(GEMINI_PAYLOAD)
    poisoned["barrier_state"] = "verified"  # model claims verified
    poisoned["potential_consequence"] = "confined_space_atmosphere"  # exposure leak

    ev = _stub_pipeline(poisoned, {}).analyze(
        "CONF-ENTRY-3", OBSERVATION, provider="llm"
    ).event
    # Negation engine is authoritative: the narrative says the controls were
    # not verified.
    assert ev.barrier == "confined_space_procedure"
    assert ev.barrier_state == "not_verified"
    # Deterministic consequence from grounded hazard/exposure: never an
    # exposure code.
    assert ev.potential_consequence in CONSEQUENCE_VALUES
    assert ev.potential_consequence not in EXPOSURE_VALUES
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.potential_consequence_basis == "model_inference"
    assert ev.sif.classification == "high"
    assert ev.sif.basis == "rule_inference"


def test_unknown_kept_when_no_evidence_for_any_canonical_barrier():
    """No narrative evidence for a control -> barrier stays unknown and is
    surfaced as a missing critical field (needs_review), never guessed."""
    narrative = "The crew performed the scheduled routine walkthrough."
    payload = {
        "activity": "unknown",
        "task_phase": "maintenance",
        "hazard": "unknown",
        "energy": "unknown",
        "barrier": "unknown",
        "barrier_state": "unknown",
        "exposure": "unknown",
        "actual_consequence": "unknown",
        "potential_consequence": "unknown",
        "location": "unknown",
        "life_saving_rules": [],
        "evidence": [],
        "confidence": 0.5,
    }
    result = _stub_pipeline(payload, {}).analyze(
        "CONF-ENTRY-4", narrative, provider="llm"
    )
    assert result.provider == "llm"
    ev = result.event
    assert ev.barrier == "unknown"
    assert "barrier" in ev.missing_fields
    assert ev.needs_review is True
    # The canonical barrier vocabulary was not weakened by the fix.
    assert "confined_space_procedure" in BARRIER_VALUES