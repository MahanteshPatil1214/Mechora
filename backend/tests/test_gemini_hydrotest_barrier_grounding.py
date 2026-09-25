"""Regression: barrier grounding in the Gemini extraction path.

The hydro-testing report describes only the hazard and the EVENT (pressurized
water/gas, a sudden pressure release, a ruptured valve) and never names the
REQUIRED control. Gemini must not turn a hazardous-energy term ("pressure")
into evidence for ``energy_isolation``:

* a hazardous-energy term is ENERGY evidence, never barrier evidence,
* barrier = energy_isolation REQUIRES language about the isolation CONTROL
  (isolation / lockout/tag-out / zero energy / depressurization / venting),
* a pressure release or a ruptured valve is an event, not proof that the
  required barrier failed,
* barrier and barrier_state stay UNKNOWN when no control is named,
* the deterministic safety layers (negation engine, SIF, LSR) stay untouched
  and authoritative; only ungrounded LLM-proposed barriers are downgraded.

The Gemini client is stubbed; no live API call is made here.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.config import get_settings
from app.services.extraction.llm_extractor import (
    _SYSTEM_INSTRUCTION,
    _build_prompt,
)
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

HYDROTEST_NARRATIVE = (
    "During hydro-testing of the new pipeline at NHK-162, personnel were "
    "working near the valve when a sudden pressure release occurred and the "
    "valve ruptured."
)

# Exactly the ungrounded output reported in the field: Gemini proposed
# energy_isolation using "pressure" as its barrier evidence and "failed" state.
HYDROTEST_PAYLOAD = {
    "activity": "testing",
    "task_phase": "operation",
    "hazard": "pressurized pipeline during hydro-testing",
    "energy": "pressurized_gas",
    "unsafe_action": "working near the valve during hydro-testing",
    "unsafe_condition": "sudden pressure release",
    "barrier": "energy_isolation",
    "barrier_state": "failed",
    "exposure": "unknown",
    "actual_consequence": "unknown",
    "potential_consequence": "unknown",
    "location": "unknown",
    "life_saving_rules": ["energy_isolation"],
    "evidence": ["pressure"],
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


def test_hydrotest_pressure_release_does_not_infer_energy_isolation():
    """A narrative with only hydro-testing / pressure / release / rupture
    provides no evidence for any required control: the LLM-proposed
    energy_isolation is not grounded and must be downgraded to UNKNOWN, along
    with its barrier state."""
    calls: dict = {}
    result = _stub_pipeline(HYDROTEST_PAYLOAD, calls).analyze(
        "HYDRO-1", HYDROTEST_NARRATIVE, provider="llm"
    )
    assert calls["contents"], "Gemini client must actually be invoked"
    assert result.provider == "llm"
    assert result.fallback_used is False

    ev = result.event
    # The hazardous energy survives (pressure IS legitimate energy evidence)...
    assert ev.energy == "pressurized_gas"
    # ...but no control is named, so no barrier and no barrier state.
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"
    assert ev.barrier != "energy_isolation"
    assert "barrier" in ev.missing_fields
    assert "barrier_state" in ev.missing_fields
    assert ev.needs_review is True


def test_pressure_never_becomes_barrier_evidence():
    """'pressure' may be the evidence span for the energy field; it must never
    appear as barrier evidence or as the basis for a barrier inference."""
    ev = _stub_pipeline(HYDROTEST_PAYLOAD, {}).analyze(
        "HYDRO-2", HYDROTEST_NARRATIVE, provider="llm"
    ).event

    # Correct use: "pressure" grounds the ENERGY value.
    assert "pressure" in ev.field_evidence.get("energy", "")
    assert ev.field_basis["energy"] == "explicit"

    # Forbidden use: "pressure" is NOT barrier evidence.
    assert not ev.field_evidence.get("barrier", "")
    assert ev.field_basis["barrier"] == "unknown"
    assert ev.field_basis["barrier_state"] == "unknown"

    # No evidence record is attributed to a barrier field.
    assert all(
        e.span != "pressure" or not ev.field_evidence.get("barrier")
        for e in ev.evidence
    )


def test_extraction_instructions_teach_energy_terms_are_not_barrier_evidence():
    """The instructions must encode the barrier-grounding rule so the model
    never proposes energy_isolation from a bare pressure term and never marks
    barrier_state failed from a release/rupture event."""
    instruction = _SYSTEM_INSTRUCTION
    assert "is NOT a safety barrier" in instruction
    assert "never barrier evidence" in instruction
    assert "must NEVER become the" in instruction
    assert "evidence for barrier = energy_isolation" in instruction
    assert "energy_isolation REQUIRES language about the ISOLATION" in instruction
    assert "describes the EVENT, not the state of an isolation control" in instruction
    assert 'NEVER makes barrier_state "failed"' in instruction
    assert 'no control named), barrier_state = "unknown"' in instruction
    assert "can never be the evidence span for barrier" in instruction
    assert "A pressure release or a ruptured valve alone is NOT evidence" in instruction
    assert "required barrier failed" in instruction

    extractor = _stub_pipeline(HYDROTEST_PAYLOAD, {}).llm_extractor
    prompt = _build_prompt(extractor._vocab(get_ontology()))
    assert "NEVER barrier evidence" in prompt
    assert "Choose barrier = energy_isolation only when" in prompt
    assert "not proof that the required barrier failed" in prompt
    assert "When barrier = \"unknown\"" in prompt


def test_explicit_control_language_still_grounds_energy_isolation():
    """The grounding guard must not reject a barrier the narrative genuinely
    establishes: explicit isolation-control language (verified too late, here)
    keeps energy_isolation and its deterministic not_verified state."""
    narrative = (
        "During hydro-testing of the new pipeline at NHK-162, personnel worked "
        "near the valve before the energy isolation was verified; a sudden "
        "pressure release occurred and the valve ruptured."
    )
    payload = dict(HYDROTEST_PAYLOAD)
    payload["barrier_state"] = "not_verified"
    payload["evidence"] = ["energy isolation was verified"]

    ev = _stub_pipeline(payload, {}).analyze(
        "HYDRO-3", narrative, provider="llm"
    ).event
    # Barrier spelling in the narrative grounds the proposed value.
    assert ev.barrier == "energy_isolation"
    assert "energy isolation" in ev.field_evidence.get("barrier", "")
    # The deterministic negation engine is authoritative for the state.
    assert ev.barrier_state == "not_verified"