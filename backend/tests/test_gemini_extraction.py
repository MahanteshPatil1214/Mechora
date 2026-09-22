"""Gemini extraction path tests.

Covers the google.genai integration and the consequence contract:

1. Migration: the extractor talks to google.genai (api key + model from
   settings, JSON output, temperature 0) — not the deprecated generativeai SDK.
2. Steam-pipeline observation (energy=thermal_energy,
   exposure=uncontrolled_steam_release, barrier=energy_isolation,
   barrier_state=not_verified, location=pump_station, task_phase=maintenance):
   Gemini supplies language/evidence; the deterministic rules layer stays
   authoritative for potential consequence and SIF classification.
3. An invalid Gemini potential_consequence (an exposure code) is normalized to
   "unknown" instead of aborting the whole LLM path into the rules fallback.

The Gemini client is always stubbed; no real API call is made.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from typing import get_args

import pytest

from app.config import get_settings
from app.models.safety_event import CONSEQUENCE_CODES, EXPOSURE_CODES, LLMExtraction
from app.services.extraction.llm_extractor import _normalize_payload
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

CONSEQUENCE_VALUES = frozenset(get_args(CONSEQUENCE_CODES))
EXPOSURE_VALUES = frozenset(get_args(EXPOSURE_CODES))

STEAM_NARRATIVE = (
    "During pump maintenance at the pump station, the steam line energy "
    "isolation was NOT verified before work began. Hot steam was released "
    "when the joint was opened."
)

# Realistic Gemini JSON for the steam observation, INCLUDING the bug this suite
# guards: an exposure code (thermal_burn) leaked into potential_consequence.
STEAM_PAYLOAD = {
    "activity": "pump_maintenance",
    "task_phase": "maintenance",
    "hazard": "pressurized hot steam",
    "energy": "thermal_energy",
    "unsafe_action": "opened the joint without isolating the steam line",
    "unsafe_condition": "energy isolation was not verified",
    "barrier": "energy_isolation",
    "barrier_state": "not_verified",
    "exposure": "uncontrolled_steam_release",
    "actual_consequence": "steam scald",
    "potential_consequence": "thermal_burn",
    "location": "pump_station",
    "life_saving_rules": ["energy_isolation"],
    "evidence": [
        "energy isolation was NOT verified",
        "steam was released",
    ],
    "confidence": 0.9,
}


def _pipeline() -> AnalysisPipeline:
    return AnalysisPipeline(get_ontology(), get_settings())


def _stub_pipeline(payload: dict, calls: dict):
    """Return a pipeline whose LLM path returns ``payload`` JSON via a fake
    google.genai-style client (records the request shape in ``calls``)."""
    pipeline = _pipeline()

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls["model"] = model
            calls["contents"] = contents
            calls["config"] = config
            return SimpleNamespace(text=json.dumps(payload))

    class _FakeClient:
        def __init__(self, api_key=None):
            calls["api_key"] = api_key
            self.models = _FakeModels()

    pipeline.llm_extractor._client = _FakeClient()
    return pipeline


# ---------------------------------------------------------------------------
# Steam-pipeline observation: Gemini language + deterministic safety reasoning
# ---------------------------------------------------------------------------


def test_steam_pipeline_observation_uses_gemini_not_rules():
    calls: dict = {}
    result = _stub_pipeline(STEAM_PAYLOAD, calls).analyze(
        "OIL-OBS-STEAM-1", STEAM_NARRATIVE, provider="llm"
    )
    assert calls, "Gemini client must actually be invoked"

    assert result.provider == "llm"
    assert result.resolved_provider == "llm"
    assert result.fallback_used is False
    assert result.requested_provider == "llm"

    ev = result.event
    assert ev.energy == "thermal_energy"
    assert ev.exposure == "uncontrolled_steam_release"
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"
    assert ev.location == "pump_station"
    assert ev.task_phase == "maintenance"

    # Potential consequence contract: stays inside the existing enum and never
    # picks up the exposure-code contamination (thermal_burn).
    assert ev.potential_consequence in CONSEQUENCE_VALUES
    assert ev.potential_consequence not in EXPOSURE_VALUES
    assert ev.potential_consequence == "serious_injury_or_fatality"


def test_steam_pipeline_deterministic_sif_matches_rules_path():
    """SIF classification is decided by deterministic safety reasoning, not by
    the model: the LLM path reaches the identical SIF and consequence verdict
    the rules path produces for the same canonical hazard."""
    ev_llm = _stub_pipeline(STEAM_PAYLOAD, {}).analyze(
        "OIL-OBS-STEAM-2", STEAM_NARRATIVE, provider="llm"
    ).event
    ev_rules = _pipeline().analyze(
        "OIL-OBS-STEAM-3", STEAM_NARRATIVE, provider="rules"
    ).event

    assert ev_llm.sif.classification == ev_rules.sif.classification == "high"
    assert ev_llm.sif.basis == "rule_inference"
    assert ev_llm.sif.classification in {"high", "medium", "low", "needs_review"}
    assert ev_llm.potential_consequence == ev_rules.potential_consequence
    assert ev_llm.potential_consequence_basis == "model_inference"


# ---------------------------------------------------------------------------
# Invalid model value must not abort the LLM path (no unnecessary fallback)
# ---------------------------------------------------------------------------


def test_exposure_code_as_consequence_does_not_fall_back_to_rules():
    result = _stub_pipeline(STEAM_PAYLOAD, {}).analyze(
        "OIL-OBS-STEAM-4", STEAM_NARRATIVE, provider="llm"
    )
    # The poisoned field was normalized, not fatal: Gemini path still wins.
    assert result.provider == "llm"
    assert result.fallback_used is False


def test_extract_normalizes_poisoned_consequence_to_unknown():
    extractor = _stub_pipeline(STEAM_PAYLOAD, {}).llm_extractor
    raw, meta = extractor.extract("OIL-OBS-STEAM-5", STEAM_NARRATIVE)
    assert isinstance(raw, LLMExtraction)
    assert meta == {"provider": "llm"}
    assert raw.potential_consequence == "unknown"


# ---------------------------------------------------------------------------
# Boundary normalization contract
# ---------------------------------------------------------------------------


def test_normalize_payload_degrades_invalid_canonical_values():
    payload = {
        "activity": "not-a-code",
        "task_phase": 42,
        "energy": "thermal_energy",
        "barrier": "energy_isolation",
        "barrier_state": "not_verified",
        "exposure": "uncontrolled_steam_release",
        "potential_consequence": "uncontrolled_steam_release",
        "location": "pump_station",
        "confidence": "0.9",
        "life_saving_rules": ["energy_isolation", "bogus-rule", 7],
        "evidence": ["ok", 1, None],
    }
    normalized = _normalize_payload(payload)

    assert normalized["activity"] == "unknown"
    assert normalized["task_phase"] == "unknown"
    assert normalized["potential_consequence"] == "unknown"
    assert normalized["life_saving_rules"] == ["energy_isolation"]
    assert normalized["evidence"] == ["ok"]
    assert normalized["confidence"] == 0.0  # non-numeric coerced, not fatal


def test_normalize_payload_drops_unknown_keys_and_truncates_text():
    payload = {
        "activity": "pump_maintenance",
        "hazard": "x" * 500,
        "evidence": ["e"] * 100,
        "mystery_field": "leak",
    }
    normalized = _normalize_payload(payload)
    assert "mystery_field" not in normalized
    assert normalized["hazard"] == "x" * 300
    assert len(normalized["evidence"]) == 40


def test_normalize_payload_requires_json_object():
    with pytest.raises(ValueError):
        _normalize_payload(["not", "a", "dict"])


# ---------------------------------------------------------------------------
# google.genai migration shape (import-level, client stubbed via sys.modules)
# ---------------------------------------------------------------------------


def test_extractor_uses_google_genai_client(monkeypatch):
    calls: dict = {}

    class _FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls["call"] = SimpleNamespace(
                model=model, contents=contents, config=config
            )
            return SimpleNamespace(text=json.dumps(STEAM_PAYLOAD))

    class _FakeClient:
        def __init__(self, api_key=None):
            calls["api_key"] = api_key
            self.models = _FakeModels()

    # Real module objects so the from-imports resolve to the fake SDK. The
    # ``google`` namespace package may already hold the real ``genai`` object
    # from earlier tests, so both sys.modules and the package attribute are
    # overridden.
    fake_genai = ModuleType("google.genai")
    fake_genai.Client = _FakeClient
    fake_types = ModuleType("google.genai.types")
    fake_types.GenerateContentConfig = _FakeConfig
    fake_genai.types = fake_types
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)
    import google as google_pkg  # noqa: PLC0415

    if hasattr(google_pkg, "genai"):
        monkeypatch.setattr(google_pkg, "genai", fake_genai)

    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    extractor = pipeline.llm_extractor

    raw, meta = extractor.extract("OIL-OBS-STEAM-6", STEAM_NARRATIVE)
    assert isinstance(raw, LLMExtraction)
    assert meta == {"provider": "llm"}

    settings = get_settings()
    assert calls["api_key"] == settings.gemini_api_key
    call = calls["call"]
    assert call.model == settings.gemini_model
    assert STEAM_NARRATIVE in call.contents
    assert "CONSEQUENCE (possible outcome" in call.contents
    cfg = call.config.kwargs
    assert cfg["response_mime_type"] == "application/json"
    assert cfg["temperature"] == 0.0
    assert "EXPOSURE and CONSEQUENCE are DIFFERENT" in cfg["system_instruction"]
    assert "NEVER copy an" in cfg["system_instruction"]
    assert "EXPOSURE code into potential_consequence" in cfg["system_instruction"]
    assert "thermal_burn" in cfg["system_instruction"]
    assert "uncontrolled_steam_release are exposure codes" in cfg["system_instruction"]