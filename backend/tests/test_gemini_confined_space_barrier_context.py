"""Regression: Gemini must infer a REQUIRED safety control from context, and
the pipeline must not let an ungrounded barrier or a lost confidence through.

Background (the field failure this file pins). A live Gemini run on a confined
-space entry narrative returned every surrounding field correctly
(``activity=confined_space_entry``, ``task_phase=inspection``,
``energy=flammable_atmosphere``, ``exposure=confined_space_atmosphere``) but
returned ``barrier=unknown`` and therefore ``barrier_state=unknown`` - even
though the narrative names the required control outright ("made safe for
entry", "required entry checks") and the model had already quoted those exact
spans in its own evidence array.

The cause was a prompt that taught barrier inference as a list of near-literal
trigger phrases guarded by repeated "never guess" pressure: a control described
by its PURPOSE or its FAILURE ("the required entry checks were never
completed") did not reach the canonical code. The inversion chain required is:

    narrative evidence -> required safety control -> canonical barrier
                       -> barrier state -> LSR mapping

Two properties must hold simultaneously, and this file asserts both:

* the control IS inferred contextually -> ``confined_space_procedure`` (an
  existing canonical code; no new ontology code is introduced), and
* it is NOT inferred from the words "confined space" alone. A narrative with no
  supporting control evidence must still yield ``unknown``, because the
  pipeline grounds every LLM-proposed barrier in a verbatim control span.

``barrier_state`` stays where it already belongs: the deterministic negation
engine, not Gemini. These tests therefore assert the ENGINE's reading of the
narrative and that the model's own ``barrier_state`` is discarded.

The Gemini client is stubbed for the deterministic tests. One opt-in live test
runs the real model when GEMINI_API_KEY is present, because a stubbed payload
cannot detect a prompt that fails to teach the mapping in the first place.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.services.extraction.llm_extractor import (
    _SYSTEM_INSTRUCTION,
    _build_prompt,
)
from app.services.negation.engine import NegationEngine
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

# --------------------------------------------------------------------------
# Narratives
# --------------------------------------------------------------------------

# The exact reported narrative. The required control is expressed only through
# purpose/failure wording: "isolated and made safe for entry", "did not verify",
# "was not confirmed safe", "had not been established", "without completing the
# required entry checks". No canonical barrier name, no "confined space" label.
TARGET_NARRATIVE = (
    "Before entering the storage vessel to inspect its interior, the "
    "maintenance team did not verify that the vessel had been properly "
    "isolated and made safe for entry. The atmosphere was not confirmed safe, "
    "ventilation had not been established, and the worker entered the vessel "
    "without completing the required entry checks."
)

# Semantic variation: different words, same required safety control. Deliberately
# avoids the target's vocabulary ("made safe for entry" / "required entry
# checks") so a memorized-sentence implementation cannot satisfy it.
VARIATION_NARRATIVE = (
    "A technician climbed into an unventilated process vessel to examine the "
    "internal coating. The pre-entry gas test had not been performed and the "
    "vessel had not been purged or certified safe, yet the entry proceeded "
    "without a completed entry permit or an attendant posted at the opening."
)

# A SECOND variation, worded as an obligation rather than a failure, to prove the
# inference is not tied to negated phrasing either.
OBLIGATION_NARRATIVE = (
    "The shift supervisor scheduled the tank-cleaning entry for the following "
    "week. Vessel entry was to be authorized under the site confined space "
    "permit, with atmospheric testing and ventilation arranged beforehand."
)

# Negative control: the words "confined space" and a vessel entry, but NO
# evidence of any required control being named, failed or relied upon.
CONFINED_SPACE_WORDS_ONLY = (
    "The technician entered a confined space to retrieve a toolbox."
)


def _pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(get_ontology(), get_settings())


def _stub_pipeline(payload: dict, calls: dict | None = None):
    """Pipeline whose LLM path returns ``payload`` via a fake google.genai
    client, recording the prompt actually sent."""
    pipeline = _pipeline()
    calls = calls if calls is not None else {}

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


def _model_payload(**overrides) -> dict:
    """A well-formed Gemini response for a confined-space entry narrative."""
    payload = {
        "activity": "confined_space_entry",
        "task_phase": "inspection",
        "hazard": "unverified atmosphere inside the storage vessel",
        "energy": "flammable_atmosphere",
        "unsafe_action": "entered the vessel without completing the entry checks",
        "unsafe_condition": "atmosphere not confirmed safe, ventilation not established",
        "barrier": "confined_space_procedure",
        "barrier_state": "not_verified",
        "exposure": "confined_space_atmosphere",
        "actual_consequence": "unknown",
        "potential_consequence": "serious_injury_or_fatality",
        "location": "unknown",
        "life_saving_rules": ["confined_space_entry", "gas_testing"],
        "evidence": [
            "did not verify that the vessel had been properly isolated and made safe for entry",
            "The atmosphere was not confirmed safe, ventilation had not been established",
            "without completing the required entry checks",
        ],
        "confidence": 0.9,
    }
    payload.update(overrides)
    return payload


def _flat(text: str) -> str:
    """Collapse whitespace so assertions survive harmless re-wrapping."""
    return " ".join(text.split())


def _prompt_text() -> str:
    return _build_prompt(
        _stub_pipeline({}).llm_extractor._vocab(get_ontology())
    )


# --------------------------------------------------------------------------
# 1. The prompt must teach CONTEXTUAL required-control inference
# --------------------------------------------------------------------------


def test_prompt_teaches_required_safety_control_inference():
    """A control named by its PURPOSE or FAILURE maps to the canonical barrier
    without the canonical name appearing in the narrative. This is the exact
    gap that shipped: the narrative says "made safe for entry" and Gemini
    answered barrier=unknown."""
    for text, label in ((_flat(_SYSTEM_INSTRUCTION), "system instruction"),
                        (_flat(_prompt_text()), "prompt")):
        # The inversion chain, in order.
        assert ("NARRATIVE EVIDENCE -> REQUIRED SAFETY CONTROL -> "
                "CANONICAL BARRIER") in text, f"chain missing from {label}"
        assert "BARRIER STATE -> LSR MAPPING" in text, label
        # The control is identified, then the code is looked up.
        assert "REQUIRED SAFETY CONTROL" in text, label
        # Requiring the canonical NAME to appear is exactly the bug.
        assert "NOT require the canonical barrier" in text, label
        # The specific target-style phrases must be taught as triggers.
        assert "made safe for entry" in text, label
        assert "required entry checks" in text, label
        assert "without completing the required entry checks" in text, label


def test_prompt_teaches_a_failed_control_is_still_that_barrier():
    """The described control keeps its canonical identity when the narrative
    reports it as missing/unverified - the failure belongs to barrier_state."""
    instruction = _SYSTEM_INSTRUCTION
    assert "MISSING" in instruction
    assert "UNVERIFIED" in instruction
    assert "FAILED" in instruction
    assert "INEFFECTIVE" in instruction
    assert "Do not return" in instruction
    assert (
        "Do not return\n   \"unknown\" for the barrier merely because the "
        "control failed" in instruction
    ), "a failed control must not collapse the barrier to unknown"


def test_prompt_teaches_entry_control_precedence_over_isolation():
    """"isolated and made safe for entry" is ONE entry-control obligation, not a
    contest between confined_space_procedure and energy_isolation, and it is
    never a reason to answer unknown."""
    for text, label in ((_flat(_SYSTEM_INSTRUCTION), "system instruction"),
                        (_flat(_prompt_text()), "prompt")):
        assert "ENTRY-CONTROL PRECEDENCE" in text, label
        assert "must not displace confined_space_procedure" in text, label


def test_prompt_forbids_confined_space_keyword_only_inference():
    """The negative half of the contract: the words "confined space" alone are
    never enough. Without supporting evidence the barrier stays unknown."""
    for text, label in ((_flat(_SYSTEM_INSTRUCTION), "system instruction"),
                        (_flat(_prompt_text()), "prompt")):
        assert "not sufficient" in text.lower(), label
        assert ("infer confined_space_procedure from that label alone"
                in text), label
        assert 'barrier = "unknown"' in text, label


def test_prompt_delegates_barrier_state_to_the_deterministic_engine():
    """barrier_state is already computed deterministically after extraction, so
    Gemini must not be asked to duplicate that logic. The prompt states the
    engine is authoritative; the pipeline proves it."""
    for text, label in ((_flat(_SYSTEM_INSTRUCTION), "system instruction"),
                        (_flat(_prompt_text()), "prompt")):
        assert "deterministic negation engine" in text, label
        assert ("not your decision" in text.lower()
                or "not yours to decide" in text.lower()), label


def test_prompt_keeps_pressure_out_of_barrier_evidence():
    """The pre-existing anti-fabrication contract must survive the rewrite: a
    hazardous-energy term is never barrier evidence for energy_isolation."""
    assert "is NOT a safety barrier" in _SYSTEM_INSTRUCTION
    assert "never barrier evidence" in _SYSTEM_INSTRUCTION
    assert "must NEVER become the" in _SYSTEM_INSTRUCTION
    assert "A pressure release or a ruptured valve alone is NOT evidence" in (
        _SYSTEM_INSTRUCTION
    )


# --------------------------------------------------------------------------
# 2. Exact target narrative -> the full expected event
# --------------------------------------------------------------------------


def test_target_narrative_yields_full_expected_event():
    """Test 1 from the report: the exact target narrative, asserting every
    expected field including the deterministic SIF verdict."""
    result = _stub_pipeline(_model_payload()).analyze(
        "CSE-TARGET-1", TARGET_NARRATIVE, provider="llm"
    )
    assert result.provider == "llm"
    assert result.fallback_used is False

    ev = result.event
    assert ev.activity == "confined_space_entry"
    assert ev.task_phase == "inspection"
    assert ev.energy == "flammable_atmosphere"
    assert ev.barrier == "confined_space_procedure"
    assert ev.exposure == "confined_space_atmosphere"
    assert ev.barrier_state == "not_verified"
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.location == "unknown"
    assert ev.sif.classification == "high"
    assert ev.missing_fields == []
    assert ev.needs_review is False


def test_target_narrative_barrier_evidence_is_a_verbatim_control_span():
    """required_barrier evidence must point at exact narrative fragments naming
    the control, not at a canonical string and not at a hazard word."""
    ev = _stub_pipeline(_model_payload()).analyze(
        "CSE-TARGET-2", TARGET_NARRATIVE, provider="llm"
    ).event

    barrier_span = ev.field_evidence.get("barrier", "")
    assert barrier_span in TARGET_NARRATIVE, "barrier evidence must be verbatim"
    assert barrier_span in ("required entry checks", "entry checks",
                            "made safe for entry"), barrier_span
    assert ev.field_basis["barrier"] == "explicit"
    # Never a hazardous-energy term as the basis for a barrier.
    assert barrier_span.lower() not in ("pressure", "isolated", "atmosphere")


def test_target_narrative_barrier_state_evidence_is_verbatim_negation():
    """barrier_state evidence must point at the explicit non-verification."""
    ev = _stub_pipeline(_model_payload()).analyze(
        "CSE-TARGET-3", TARGET_NARRATIVE, provider="llm"
    ).event

    state_span = ev.field_evidence.get("barrier_state", "")
    assert state_span in TARGET_NARRATIVE, "barrier_state evidence must be verbatim"
    # The full causal sentence carries the non-verification wording.
    assert "was not confirmed safe" in state_span
    assert "without completing the required entry checks" in state_span
    assert ev.field_basis["barrier_state"] == "explicit"


def test_barrier_state_comes_from_the_negation_engine_not_gemini():
    """The model proposes "verified"; the deterministic engine owns the value
    and reads the narrative's explicit non-verification."""
    poisoned = _model_payload(barrier_state="verified", confidence=0.9)
    ev = _stub_pipeline(poisoned).analyze(
        "CSE-TARGET-4", TARGET_NARRATIVE, provider="llm"
    ).event
    assert ev.barrier_state == "not_verified"

    # And the engine reaches that verdict from the narrative alone.
    direct = NegationEngine(get_ontology()).classify_barrier(
        "confined_space_procedure", TARGET_NARRATIVE
    )
    assert direct.state == "not_verified"
    assert direct.evidence_span


# --------------------------------------------------------------------------
# 3. Semantic variation - the implementation must generalize
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "report_id,narrative",
    [("CSE-VAR-1", VARIATION_NARRATIVE)],
)
def test_semantic_variations_reach_the_same_canonical_codes(report_id, narrative):
    """Test 2 from the report: a differently-worded narrative expressing the same
    safety mechanism must reach the same canonical codes. It does not reuse the
    target sentence, so a memorized implementation fails here."""
    ev = _stub_pipeline(_model_payload()).analyze(
        report_id, narrative, provider="llm"
    ).event

    assert ev.activity == "confined_space_entry"
    assert ev.barrier == "confined_space_procedure"
    assert ev.barrier_state == "not_verified"
    assert ev.energy == "flammable_atmosphere"
    assert ev.exposure == "confined_space_atmosphere"
    assert ev.sif.classification == "high"

    # Evidence is grounded in THIS narrative, verbatim.
    assert ev.field_evidence.get("barrier", "") in narrative
    for span in ev.field_evidence.values():
        assert span in narrative, f"evidence not verbatim for {report_id}: {span!r}"


def test_barrier_state_is_not_hardcoded_to_the_failure_reading():
    """A third wording states the entry control as a properly arranged
    OBLIGATION rather than a failure. The barrier is still reached (the control
    is named), but the deterministic engine reads the state as verified - proof
    that barrier_state comes from the narrative, not from a memorized
    not_verified."""
    ev = _stub_pipeline(_model_payload(barrier_state="verified")).analyze(
        "CSE-VAR-2", OBLIGATION_NARRATIVE, provider="llm"
    ).event
    assert ev.barrier == "confined_space_procedure"
    assert ev.barrier_state == "verified", (
        "a narrative describing properly arranged entry controls must not be "
        "forced into not_verified"
    )
    assert ev.field_evidence.get("barrier", "") in OBLIGATION_NARRATIVE


def test_variation_does_not_depend_on_the_target_wording():
    """Explicit anti-hardcoding guard: no fragment of the target narrative is
    required. The variation shares none of its control wording, yet resolves to
    the same barrier through the ontology's own vocabulary."""
    ev = _stub_pipeline(_model_payload()).analyze(
        "CSE-VAR-3", VARIATION_NARRATIVE, provider="llm"
    ).event
    assert ev.barrier == "confined_space_procedure"
    # The trigger that actually fired comes from the variation itself.
    assert any(
        token in ev.field_evidence.get("barrier", "")
        for token in ("entry permit", "entry", "gas", "atmosphere")
    )
    assert "made safe for entry" not in VARIATION_NARRATIVE
    assert "required entry checks" not in VARIATION_NARRATIVE


# --------------------------------------------------------------------------
# 4. No new ontology code, and the canonical one is unchanged
# --------------------------------------------------------------------------


def test_no_new_ontology_code_was_introduced():
    """The fix must reuse the existing canonical code, not mint a new one."""
    ontology = get_ontology()
    codes = ontology.codes("barrier")
    assert "confined_space_procedure" in codes
    assert len(codes) == len(set(codes))
    # Nothing entry-related beyond the pre-existing code.
    entry_like = [c for c in codes if "confined" in c or "entry" in c]
    assert entry_like == ["confined_space_procedure"], entry_like

    states = get_settings()  # touch settings so config is exercised
    assert states is not None
    from app.models.safety_event import BARRIER_STATE_CODES
    from typing import get_args
    assert "not_verified" in get_args(BARRIER_STATE_CODES)


def test_barrier_is_not_derived_from_the_life_saving_rule():
    """A proposed confined-space LSR must never manufacture the barrier."""
    payload = _model_payload(
        barrier="unknown", life_saving_rules=["confined_space_entry", "gas_testing"],
        evidence=[],
    )
    ev = _stub_pipeline(payload).analyze(
        "CSE-NOLSR-1", "The crew continued work through the shift.", provider="llm"
    ).event
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"


# --------------------------------------------------------------------------
# 5. The anti-hardcoding guard: the pipeline grounds every proposed barrier
# --------------------------------------------------------------------------


def test_confined_space_words_alone_cannot_manufacture_the_barrier():
    """Even if Gemini proposes confined_space_procedure for a narrative that
    only says "confined space", the pipeline has no verbatim control span to
    ground it and downgrades it to unknown. This is what makes the inference
    safe rather than a keyword match."""
    ev = _stub_pipeline(
        _model_payload(evidence=["confined space"])
    ).analyze(
        "CSE-ANTI-1", CONFINED_SPACE_WORDS_ONLY, provider="llm"
    ).event

    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"
    assert "barrier" in ev.missing_fields
    assert ev.needs_review is True
    assert not ev.field_evidence.get("barrier")
    assert ev.field_basis["barrier"] == "unknown"


def test_ungrounded_barrier_and_state_are_both_suppressed_together():
    """barrier_state cannot outlive its barrier: no grounded control means no
    attributable state, so both fields fall back to unknown together."""
    ev = _stub_pipeline(
        _model_payload(barrier_state="not_verified", evidence=["confined space"])
    ).analyze("CSE-ANTI-2", CONFINED_SPACE_WORDS_ONLY, provider="llm").event
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"


# --------------------------------------------------------------------------
# 6. Extraction confidence must not be silently lost on the LLM path
# --------------------------------------------------------------------------


def test_llm_path_honours_the_models_self_assessed_confidence():
    """Regression: the LLM path never read ``extraction.confidence``, so an LLM
    analysis leaked the SafetyEvent default of 0.0 and the UI rendered
    "EXTRACTION CONFIDENCE 0%" after a successful multi-field extraction."""
    ev = _stub_pipeline(_model_payload(confidence=0.9)).analyze(
        "CSE-CONF-1", TARGET_NARRATIVE, provider="llm"
    ).event
    assert ev.confidence == 0.9
    assert ev.confidence > 0.0


def test_llm_confidence_survives_an_ungrounded_barrier():
    """The 0% symptom was strongest exactly when the barrier failed to ground,
    because that is the branch that used to leave confidence untouched."""
    ev = _stub_pipeline(
        _model_payload(barrier="unknown", barrier_state="unknown", confidence=0.9)
    ).analyze("CSE-CONF-2", CONFINED_SPACE_WORDS_ONLY, provider="llm").event
    assert ev.barrier == "unknown"
    assert ev.confidence == 0.9, "confidence must not collapse to the 0.0 default"


def test_llm_confidence_is_not_the_barrier_state_confidence():
    """The negation engine's confidence describes the BARRIER STATE, a different
    quantity; it must not masquerade as whole-extraction confidence. When the
    engine is confident about not_verified (0.95) and the model self-assessed
    0.9, the event reports 0.9."""
    ev = _stub_pipeline(_model_payload(confidence=0.9)).analyze(
        "CSE-CONF-3", TARGET_NARRATIVE, provider="llm"
    ).event
    state_confidence = NegationEngine(get_ontology()).classify_barrier(
        "confined_space_procedure", TARGET_NARRATIVE
    ).confidence
    assert state_confidence != ev.confidence
    assert ev.confidence == 0.9


def test_llm_confidence_is_independent_of_barrier_grounding():
    """The reported confidence must describe the extraction, so grounding the
    barrier must not change it."""
    grounded = _stub_pipeline(_model_payload(confidence=0.75)).analyze(
        "CSE-CONF-4", TARGET_NARRATIVE, provider="llm"
    ).event
    ungrounded = _stub_pipeline(
        _model_payload(barrier="unknown", confidence=0.75)
    ).analyze("CSE-CONF-5", CONFINED_SPACE_WORDS_ONLY, provider="llm").event
    assert grounded.confidence == ungrounded.confidence == 0.75


def test_rules_path_confidence_is_unchanged():
    """The rules path already computed field-coverage confidence; the fix must
    not alter it. Recomputed here from the actual extraction so the assertion
    pins the documented formula rather than a magic number."""
    pipeline = _pipeline()
    ev = pipeline.analyze("CSE-CONF-6", TARGET_NARRATIVE, provider="rules").event
    assert 0.0 < ev.confidence <= 1.0

    coverage = pipeline.rule_extractor._overall_confidence(
        ev.activity, ev.task_phase, ev.energy, ev.barrier,
        ev.barrier_state, ev.exposure, ev.location, ev.actual_consequence,
    )
    state_confidence = pipeline.negation.classify_barrier(
        ev.barrier, TARGET_NARRATIVE
    ).confidence
    # The rules extractor keeps the greater of field coverage and the
    # barrier-state confidence (discounted), as it always has.
    assert ev.confidence == pytest.approx(
        max(round(coverage, 4), round(state_confidence * 0.9, 4))
    )


def test_confidence_stays_within_the_schema_range():
    """No provider may push confidence outside 0..1."""
    for value in (0.0, 0.5, 1.0):
        ev = _stub_pipeline(_model_payload(confidence=value)).analyze(
            "CSE-CONF-7", TARGET_NARRATIVE, provider="llm"
        ).event
        assert 0.0 <= ev.confidence <= 1.0
        assert ev.confidence == value


# --------------------------------------------------------------------------
# 7. Opt-in live check: only a real model call can catch a prompt regression
# --------------------------------------------------------------------------

# Live model checks are opt-in on top of the API key: the Gemini free tier
# allows only ~20 generate_content requests PER DAY, so an always-on live test
# would silently burn the daily quota and then skip itself. Set
# RUN_LIVE_GEMINI_TESTS=1 to spend real quota deliberately.
_LIVE_KEY = (os.environ.get("GEMINI_API_KEY", "").strip()
             or get_settings().gemini_api_key)
_RUN_LIVE = bool(_LIVE_KEY) and os.environ.get(
    "RUN_LIVE_GEMINI_TESTS", "").strip().lower() in ("1", "true", "yes")
_LIVE_REASON = ("live Gemini disabled (set RUN_LIVE_GEMINI_TESTS=1; the free "
                "tier allows only ~20 generate_content requests/day)")
if not _LIVE_KEY:
    _LIVE_REASON = "GEMINI_API_KEY not configured"


def _require_live(result):
    """Skip on a transient provider outage; a 503 is not a prompt regression."""
    detail = " ".join(
        [result.fallback_reason or "", *(result.warnings or [])]
    ).lower()
    if result.fallback_used and (
        "unavailable" in detail or "failed at runtime" in detail
    ):
        pytest.skip(f"Gemini unavailable: {detail.strip()}")
    return result


@pytest.mark.skipif(not _RUN_LIVE, reason=_LIVE_REASON)
def test_live_gemini_extracts_the_target_barrier_and_state():
    """End-to-end against the real model. Stubbed payloads cannot detect a
    prompt that fails to TEACH the mapping, which is precisely how barrier and
    barrier_state shipped as unknown while every neighbouring test passed."""
    result = _require_live(
        _pipeline().analyze("CSE-LIVE-1", TARGET_NARRATIVE, provider="llm")
    )
    assert result.provider == "llm"
    assert result.fallback_used is False, result.fallback_reason

    ev = result.event
    assert ev.activity == "confined_space_entry"
    assert ev.task_phase == "inspection"
    assert ev.energy == "flammable_atmosphere"
    assert ev.barrier == "confined_space_procedure"
    assert ev.exposure == "confined_space_atmosphere"
    assert ev.barrier_state == "not_verified"
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.location == "unknown"
    assert ev.sif.classification == "high"
    assert ev.confidence > 0.0
    assert ev.field_evidence.get("barrier", "") in TARGET_NARRATIVE


@pytest.mark.skipif(not _RUN_LIVE, reason=_LIVE_REASON)
def test_live_gemini_generalizes_to_a_semantic_variation():
    """The live model must reach the same barrier from different wording, and
    must still refuse the keyword-only narrative."""
    ev = _require_live(
        _pipeline().analyze("CSE-LIVE-2", VARIATION_NARRATIVE, provider="llm")
    ).event
    assert ev.barrier == "confined_space_procedure"
    assert ev.barrier_state == "not_verified"

    guarded = _require_live(
        _pipeline().analyze("CSE-LIVE-3", CONFINED_SPACE_WORDS_ONLY, provider="llm")
    ).event
    assert guarded.barrier == "unknown", (
        "the words 'confined space' alone must never produce the barrier"
    )
