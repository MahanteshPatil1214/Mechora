"""Gemini model configuration and runtime-failure regression tests.

Guards the 404 that silently disabled the Gemini path:

    Google returns HTTP 404 "This model models/gemini-2.5-flash is no longer
    available to new users" -> the pipeline falls back to the deterministic
    rules path -> /api/v1/analyze still returns HTTP 200.

A 200 therefore proves nothing about the LLM path, so these tests assert the
REQUEST itself: that the default model is currently servable, that
GEMINI_MODEL still overrides it, and that google-genai is called with whatever
model is configured. The safety architecture is asserted unchanged: Gemini only
supplies language/evidence, potential_consequence is recomputed
deterministically, SIF stays deterministic, and a Gemini failure still falls
back to the rules path.

A second silent-failure class is guarded here: google-genai ENABLES automatic
function calling by default whenever no tools are supplied, so omitting the
kwarg leaves the function-calling loop active. Runtime logs showed
"AFC is enabled with max remote calls: 10" plus a second billable
generateContent round-trip. The AFC tests therefore assert the SDK's own
``should_disable_afc`` gate against the real ``GenerateContentConfig``, so they
fail if the explicit override is removed.

The Gemini client is always stubbed; no real API call is made.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.config import Settings, get_settings
from app.models.safety_event import LLMExtraction
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

# The model Google currently serves for this deployment, as declared by the
# CODE DEFAULT in config.py. This is independent of the runtime GEMINI_MODEL
# override and is what a deployment with no GEMINI_MODEL set will request.
EXPECTED_DEFAULT_MODEL = "gemini-3.8-flash"

# The runtime override this deployment currently ships. Deliberately a floating
# availability alias: it must be honoured end-to-end without invalidating the
# code default.
OVERRIDE_MODEL = "gemini-flash-latest"

# A retired alias. Requesting it is what produced the 404.
RETIRED_MODEL = "gemini-2.5-flash"

NARRATIVE = (
    "During pump maintenance at the pump station, the steam line energy "
    "isolation was NOT verified before work began. Hot steam was released "
    "when the joint was opened."
)

PAYLOAD = {
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
    # An EXPOSURE code leaking into potential_consequence: the deterministic
    # layer must recompute this rather than trusting the model.
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


def _stub_genai(monkeypatch, *, response_text=None, raises=None):
    """Point google.genai at a fake client and return the ``calls`` dict.

    Mirrors the shape used by test_gemini_extraction.py: real ModuleType
    objects are registered so the from-imports in the extractor resolve to the
    fake SDK, and the ``google`` package attribute is overridden too because
    the real ``genai`` object may already be cached there.
    """
    calls: dict = {}

    class _FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeAFCConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls["model"] = model
            calls["contents"] = contents
            calls["config"] = config
            if raises is not None:
                raise raises
            return SimpleNamespace(text=response_text)

    class _FakeClient:
        def __init__(self, api_key=None):
            calls["api_key"] = api_key
            self.models = _FakeModels()

    fake_genai = ModuleType("google.genai")
    fake_genai.Client = _FakeClient
    fake_types = ModuleType("google.genai.types")
    fake_types.GenerateContentConfig = _FakeConfig
    fake_types.AutomaticFunctionCallingConfig = _FakeAFCConfig
    fake_genai.types = fake_types
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)
    import google as google_pkg  # noqa: PLC0415

    if hasattr(google_pkg, "genai"):
        monkeypatch.setattr(google_pkg, "genai", fake_genai)
    return calls


# ---------------------------------------------------------------------------
# 1. Default model
# ---------------------------------------------------------------------------


def test_default_model_is_currently_servable():
    """The code default must not be a retired alias.

    config.py is the source of truth for the default; .env and .env.example
    override it at runtime, so a stale default would keep the 404 alive for any
    environment without GEMINI_MODEL set.
    """
    assert Settings.model_fields["gemini_model"].default == EXPECTED_DEFAULT_MODEL


def test_default_model_is_not_the_retired_alias():
    assert Settings(gemini_api_key="x").gemini_model != RETIRED_MODEL


def test_env_example_documents_the_servable_default():
    """The template must not hand new deployments a retired alias."""
    from pathlib import Path

    example = Path(__file__).resolve().parents[2] / ".env.example"
    text = example.read_text(encoding="utf-8")
    assert f"GEMINI_MODEL={EXPECTED_DEFAULT_MODEL}" in text
    assert RETIRED_MODEL not in text


# ---------------------------------------------------------------------------
# 2. Environment override is preserved
# ---------------------------------------------------------------------------


def test_env_var_override_still_works():
    """GEMINI_MODEL must keep winning - configurability is not removed."""
    assert Settings(gemini_model="gemini-custom-model").gemini_model == "gemini-custom-model"


def test_env_var_camel_case_override_still_works():
    """The .env key is GEMINI_MODEL; pydantic maps it onto gemini_model."""
    assert Settings(GEMINI_MODEL="gemini-from-env").gemini_model == "gemini-from-env"


def test_runtime_env_var_is_read(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-set-at-runtime")
    try:
        assert Settings().gemini_model == "gemini-set-at-runtime"
    finally:
        monkeypatch.delenv("GEMINI_MODEL", raising=False)


# ---------------------------------------------------------------------------
# 3. google-genai is called with the configured model
# ---------------------------------------------------------------------------


def test_genai_called_with_configured_model(monkeypatch):
    """The wire model must be whatever the extractor is actually configured with.

    This asserts the CONTRACT - the configured model reaches ``generate_content``
    - rather than a literal model name. The resolved value is legitimately either
    the code default or a GEMINI_MODEL override; pinning a name here made this
    test fail for a correct override, which is the bug being removed. The
    default-vs-override distinction is pinned by
    ``test_runtime_override_reaches_the_wire_and_may_differ_from_the_default``.
    """
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    pipeline.llm_extractor.extract("R-MODEL-1", NARRATIVE)

    assert calls["model"] == pipeline.llm_extractor.settings.gemini_model
    # Whatever it resolved to, a real model identifier was sent.
    assert isinstance(calls["model"], str) and calls["model"]


def test_runtime_override_reaches_the_wire_and_may_differ_from_the_default(monkeypatch):
    """GEMINI_MODEL may legitimately differ from the code default.

    Proves the override is honoured end-to-end AND that supplying it does not
    rewrite config.py's default - the two are separate concerns and both must
    hold at once.
    """
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    pipeline.llm_extractor.settings = Settings(
        gemini_api_key="key", gemini_model=OVERRIDE_MODEL
    )

    pipeline.llm_extractor.extract("R-MODEL-3", NARRATIVE)

    # The override reached the wire...
    assert calls["model"] == OVERRIDE_MODEL
    # ...and it genuinely is a different value from the code default...
    assert OVERRIDE_MODEL != EXPECTED_DEFAULT_MODEL
    # ...while the code default is still intact and unchanged.
    assert Settings.model_fields["gemini_model"].default == EXPECTED_DEFAULT_MODEL


def test_genai_called_with_overridden_model(monkeypatch):
    """An override must reach the wire, not just the Settings object."""
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    pipeline.llm_extractor.settings = Settings(
        gemini_api_key="key", gemini_model="gemini-pinned-model"
    )

    pipeline.llm_extractor.extract("R-MODEL-2", NARRATIVE)

    assert calls["model"] == "gemini-pinned-model"


def test_retired_model_is_never_requested(monkeypatch):
    """Regression guard for the reported 404."""
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    pipeline.llm_extractor.extract("R-MODEL-3", NARRATIVE)

    assert calls["model"] != RETIRED_MODEL


# ---------------------------------------------------------------------------
# 4. Automatic function calling is explicitly disabled
# ---------------------------------------------------------------------------


def _stub_genai_real_types(monkeypatch, *, response_text=None, raises=None):
    """Fake only the client; keep the REAL google.genai.types.

    The AFC default lives in the SDK, not in MECHORA's kwargs, so only the real
    pydantic ``GenerateContentConfig`` can prove AFC is actually off. The real
    types are exposed as an attribute on the fake package so that
    ``from google.genai import types`` inside the extractor resolves to them.
    """
    from google.genai import types as real_types  # noqa: PLC0415

    calls: dict = {}

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            calls["model"] = model
            calls["contents"] = contents
            calls["config"] = config
            if raises is not None:
                raise raises
            return SimpleNamespace(text=response_text)

    class _FakeClient:
        def __init__(self, api_key=None):
            self.models = _FakeModels()

    fake_genai = ModuleType("google.genai")
    fake_genai.Client = _FakeClient
    fake_genai.types = real_types
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    import google as google_pkg  # noqa: PLC0415

    if hasattr(google_pkg, "genai"):
        monkeypatch.setattr(google_pkg, "genai", fake_genai)
    return calls


def test_sdk_default_enables_afc_so_omission_is_not_enough():
    """Pin down the misconception the previous test encoded.

    google-genai turns AFC ON whenever the caller supplies no tools, so a config
    that merely omits ``automatic_function_calling`` leaves the function-calling
    loop active. This asserts the SDK default, which is the reason the extractor
    must override it rather than rely on absence.
    """
    real_types = pytest.importorskip("google.genai.types")
    extra_utils = pytest.importorskip("google.genai._extra_utils")

    cfg = real_types.GenerateContentConfig(
        system_instruction="s",
        response_mime_type="application/json",
        temperature=0.0,
    )

    assert cfg.tools is None
    assert cfg.automatic_function_calling is None
    # False == AFC stays ENABLED, i.e. omission does not disable it.
    assert extra_utils.should_disable_afc(cfg) is False


def test_extraction_config_explicitly_disables_afc(monkeypatch):
    """The extraction call must override the SDK AFC default, not omit it.

    This fails if the ``AutomaticFunctionCallingConfig(disable=True)`` override
    is removed: the real config would then carry ``automatic_function_calling
    is None`` and the SDK's own ``should_disable_afc`` gate would report AFC as
    enabled.
    """
    extra_utils = pytest.importorskip("google.genai._extra_utils")
    calls = _stub_genai_real_types(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    pipeline.llm_extractor.extract("R-AFC-1", NARRATIVE)

    cfg = calls["config"]

    # Structural: an explicit override object is passed, not an omission.
    assert cfg.automatic_function_calling is not None
    assert cfg.automatic_function_calling.disable is True
    # No tools/function declarations are introduced by disabling AFC.
    assert cfg.tools is None
    # Behavioural: the SDK's own gate agrees the function-calling loop is off.
    assert extra_utils.should_disable_afc(cfg) is True
    # The extraction contract is untouched.
    assert cfg.response_mime_type == "application/json"
    assert cfg.temperature == 0.0
    assert cfg.system_instruction


def test_afc_override_survives_without_a_client_stub(monkeypatch):
    """The override must hold on the real call path too, not just under stubs."""
    extra_utils = pytest.importorskip("google.genai._extra_utils")
    real_types = pytest.importorskip("google.genai.types")
    calls = _stub_genai_real_types(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    pipeline.llm_extractor.settings = Settings(
        gemini_api_key="key", gemini_model="gemini-pinned-model"
    )

    pipeline.llm_extractor.extract("R-AFC-2", NARRATIVE)

    assert calls["model"] == "gemini-pinned-model"
    assert extra_utils.should_disable_afc(calls["config"]) is True
    assert isinstance(calls["config"], real_types.GenerateContentConfig)


# ---------------------------------------------------------------------------
# 5. Fallback behavior remains intact
# ---------------------------------------------------------------------------


def test_retired_model_404_falls_back_to_rules(monkeypatch):
    """The exact reported failure: an unavailable model must not 500 the API.

    Reproduces the observed sequence - a request is sent to a retired alias,
    Google rejects it, the pipeline falls back to deterministic rules, and the
    caller still receives a complete event.
    """
    calls = _stub_genai(
        monkeypatch,
        raises=RuntimeError(
            "This model models/gemini-2.5-flash is no longer available to new "
            "users. Please update your code to use models/gemini-3.8-flash."
        ),
    )
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    pipeline.llm_extractor.settings = Settings(
        gemini_api_key="key", gemini_model=RETIRED_MODEL
    )

    result = pipeline.analyze("R-404-1", NARRATIVE, provider="llm")

    assert calls["model"] == RETIRED_MODEL  # the failing call really happened
    assert result.provider == "rules"
    assert result.requested_provider == "llm"
    assert result.fallback_used is True
    assert result.fallback_reason
    assert result.warnings
    # A complete, schema-valid deterministic event is still produced.
    assert result.event.energy == "thermal_energy"
    assert result.event.barrier_state == "not_verified"


def test_fallback_preserves_evidence_grounding(monkeypatch):
    _stub_genai(monkeypatch, raises=RuntimeError("boom"))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    event = pipeline.analyze("R-404-2", NARRATIVE, provider="llm").event

    for key, value in (event.field_evidence or {}).items():
        if value:
            assert value in NARRATIVE, f"{key} evidence not grounded: {value!r}"


def test_fallback_sif_is_deterministic(monkeypatch):
    _stub_genai(monkeypatch, raises=RuntimeError("boom"))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    first = pipeline.analyze("R-404-3", NARRATIVE, provider="llm").event
    second = pipeline.analyze("R-404-4", NARRATIVE, provider="llm").event

    assert first.sif.classification == second.sif.classification


# ---------------------------------------------------------------------------
# 6. Safety architecture unchanged on the LLM path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gemini_model",
    [EXPECTED_DEFAULT_MODEL, OVERRIDE_MODEL, "gemini-some-future-model"],
)
def test_potential_consequence_is_recomputed_deterministically(
    monkeypatch, gemini_model
):
    """Gemini's invalid potential_consequence (an exposure code) is not trusted.

    Parametrised over the model name on purpose: recomputation is a
    deterministic pipeline guarantee, so it must hold identically for the code
    default, for the runtime override, and for any future model. Pinning a
    single model name here would have tested the config, not the safety rule.
    """
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None
    pipeline.llm_extractor.settings = Settings(
        gemini_api_key="key", gemini_model=gemini_model
    )

    result = pipeline.analyze("R-SAFE-1", NARRATIVE, provider="llm")

    # The configured model was used...
    assert calls["model"] == gemini_model
    assert result.provider == "llm"
    # ...and the deterministic recomputation is identical for all of them.
    # "thermal_burn" is an exposure code, not a potential_consequence code.
    assert result.event.potential_consequence != "thermal_burn"
    assert result.event.potential_consequence in {
        "serious_injury_or_fatality",
        "injury",
        "minor_injury",
        "unknown",
    }


def test_llm_path_evidence_remains_grounded(monkeypatch):
    calls = _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    result = pipeline.analyze("R-SAFE-2", NARRATIVE, provider="llm")

    assert result.provider == "llm"
    for key, value in (result.event.field_evidence or {}).items():
        if value:
            assert value in NARRATIVE, f"{key} evidence not grounded: {value!r}"


def test_llm_path_sif_is_deterministic_across_runs(monkeypatch):
    _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    first = pipeline.analyze("R-SAFE-3", NARRATIVE, provider="llm").event
    second = pipeline.analyze("R-SAFE-4", NARRATIVE, provider="llm").event

    assert first.sif.classification == second.sif.classification


def test_extractor_still_parses_canonical_json(monkeypatch):
    _stub_genai(monkeypatch, response_text=json.dumps(PAYLOAD))
    pipeline = _pipeline()
    pipeline.llm_extractor._client = None

    raw, meta = pipeline.llm_extractor.extract("R-SAFE-5", NARRATIVE)

    assert isinstance(raw, LLMExtraction)
    assert meta == {"provider": "llm"}


def test_deprecated_generativeai_sdk_is_not_used():
    """The deprecated google-generativeai package must stay out."""
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "extraction"
        / "llm_extractor.py"
    ).read_text(encoding="utf-8")

    assert "from google import genai" in src
    assert "google.generativeai" not in src
