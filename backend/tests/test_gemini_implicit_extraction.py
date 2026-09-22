"""Regression: Gemini extraction quality for implicit safety concepts.

The crude-oil transfer pump report implies its safety concepts with contextual
wording ("stored pressure", "broke the flange", "hot fluid escaped from the
connection", "hissing sound") rather than naming ontology codes. The extraction
instructions must teach Gemini to map that wording onto the existing ontology,
while the deterministic layers stay authoritative for potential consequence and
SIF. The Gemini client is stubbed; no live API call is made here.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import get_args

from app.config import get_settings
from app.models.safety_event import CONSEQUENCE_CODES, EXPOSURE_CODES
from app.services.extraction.llm_extractor import (
    _SYSTEM_INSTRUCTION,
    _build_prompt,
)
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

CONSEQUENCE_VALUES = frozenset(get_args(CONSEQUENCE_CODES))
EXPOSURE_VALUES = frozenset(get_args(EXPOSURE_CODES))

OBSERVATION = (
    "While preparing to service the crude oil transfer pump at the pump house, "
    "the maintenance crew broke the flange without first confirming that all "
    "stored pressure had been released. A hissing sound was noticed and a small "
    "amount of hot fluid escaped from the connection. The isolation had been "
    "assumed rather than independently verified, creating a potential serious "
    "injury exposure."
)

# Fixed Gemini output after the implicit-concept instruction update: contextual
# wording mapped onto existing ontology codes. potential_consequence stays
# "unknown" at the model level so the deterministic layer must derive it.
GEMINI_PAYLOAD = {
    "activity": "pump_maintenance",
    "task_phase": "pre_job",
    "hazard": "stored pressure in the crude oil transfer line",
    "energy": "pressurized_liquid",
    "unsafe_action": "broke the flange without confirming stored pressure released",
    "unsafe_condition": "isolation assumed rather than independently verified",
    "barrier": "energy_isolation",
    "barrier_state": "not_verified",
    "exposure": "uncontrolled_liquid_release",
    "actual_consequence": "unknown",
    "potential_consequence": "unknown",
    "location": "pump_station",
    "life_saving_rules": ["energy_isolation"],
    "evidence": [
        "stored pressure had been released",
        "hot fluid escaped from the connection",
    ],
    "confidence": 0.85,
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


def test_implicit_concepts_mapped_and_provider_is_gemini():
    calls: dict = {}
    result = _stub_pipeline(GEMINI_PAYLOAD, calls).analyze(
        "OIL-OBS-PUMP-1", OBSERVATION, provider="llm"
    )
    assert calls["contents"], "Gemini client must actually be invoked"
    assert result.provider == "llm"
    assert result.fallback_used is False
    assert result.warnings == []

    ev = result.event
    assert ev.energy == "pressurized_liquid"
    assert ev.exposure == "uncontrolled_liquid_release"
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"
    assert ev.location == "pump_station"
    assert ev.task_phase == "pre_job"
    assert ev.activity == "pump_maintenance"

    # Consequence contract: inside the existing enum, never an exposure code,
    # and derived by the deterministic layer even though the model said unknown.
    assert ev.potential_consequence in CONSEQUENCE_VALUES
    assert ev.potential_consequence not in EXPOSURE_VALUES
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.potential_consequence_basis == "model_inference"

    # Every claimed evidence span is verbatim from the narrative.
    for span in ev.field_evidence.values():
        assert span in OBSERVATION, f"evidence not verbatim: {span!r}"
    for evidence in ev.evidence:
        assert evidence.span in OBSERVATION, (
            f"evidence not verbatim: {evidence.span!r}"
        )


def test_deterministic_consequence_and_sif_unchanged():
    """Safety reasoning is provider-independent: the Gemini path reaches the
    same consequence and SIF verdict the rules path does for this hazard."""
    ev_llm = _stub_pipeline(GEMINI_PAYLOAD, {}).analyze(
        "OIL-OBS-PUMP-2", OBSERVATION, provider="llm"
    ).event
    ev_rules = _pipeline().analyze(
        "OIL-OBS-PUMP-3", OBSERVATION, provider="rules"
    ).event

    assert (
        ev_llm.potential_consequence
        == ev_rules.potential_consequence
        == "serious_injury_or_fatality"
    )
    assert ev_llm.sif.classification == ev_rules.sif.classification == "high"
    assert ev_llm.sif.basis == "rule_inference"
    assert ev_llm.sif.classification in {"high", "medium", "low", "needs_review"}


def test_extraction_instructions_teach_implicit_concept_mapping():
    """The instructions must encode the implicit-concept mapping so the model
    can translate contextual wording into existing ontology codes — without
    inventing codes or confusing exposure with consequence."""
    assert "stored pressure" in _SYSTEM_INSTRUCTION
    assert "crude oil" in _SYSTEM_INSTRUCTION
    assert "hissing sound" in _SYSTEM_INSTRUCTION
    assert "escaped from the connection" in _SYSTEM_INSTRUCTION
    assert "hot fluid escaped" in _SYSTEM_INSTRUCTION
    assert "pressurized_liquid" in _SYSTEM_INSTRUCTION
    assert "uncontrolled_liquid_release" in _SYSTEM_INSTRUCTION
    assert "return \"unknown\" rather than guessing" in _SYSTEM_INSTRUCTION
    assert "NEVER copy an" in _SYSTEM_INSTRUCTION
    assert "EXPOSURE and CONSEQUENCE are DIFFERENT" in _SYSTEM_INSTRUCTION

    extractor = _stub_pipeline(GEMINI_PAYLOAD, {}).llm_extractor
    prompt = _build_prompt(extractor._vocab(get_ontology()))
    assert "stored pressure" in prompt
    assert "fluid escaped" in prompt
    assert "hiss" in prompt
    assert "uncontrolled_liquid_release" in prompt
    assert (
        "potential_consequence must be exactly one of the CONSEQUENCE codes"
        in prompt
    )


def test_unknown_still_honest_when_evidence_insufficient():
    """When the mapping hints do not apply, unknown must remain the outcome."""
    narrative = "The crew followed the maintenance procedure for routine work."
    result = _stub_pipeline(
        {
            "activity": "pump_maintenance",
            "task_phase": "maintenance",
            "hazard": "unknown",
            "energy": "unknown",
            "barrier": "unknown",
            "barrier_state": "unknown",
            "exposure": "unknown",
            "actual_consequence": "unknown",
            "potential_consequence": "unknown",
            "location": "unknown",
            "confidence": 0.5,
        },
        {},
    ).analyze("OIL-OBS-PUMP-4", narrative, provider="llm")
    assert result.provider == "llm"
    assert result.fallback_used is False
    assert result.event.energy == "unknown"
    assert result.event.exposure == "unknown"
    assert result.event.potential_consequence == "unknown"