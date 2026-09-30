"""Single-analysis regression tests for POST /api/v1/analyze.

The route used to analyse TWICE per request:

    analyze.py   -> pipeline.analyze(...)          # Gemini call #1
    analyze.py   -> pipeline.to_observation(...)  # -> self.analyze()  # call #2

That doubled the LLM cost of every request and created a provenance split: the
HTTP response's ``warnings`` came from call #1 while the persisted event and
provider metadata came from call #2. If the two runs disagreed - which a
non-deterministic model, or a transient failure on the second call, will do -
the client was told one thing and another thing was written to the database.

These tests pin the fix: ONE request performs exactly ONE analysis, and the
event, provider metadata and warnings in the response all originate from that
same invocation. The deterministic safety behaviour is asserted unchanged.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.api.routes import analyze as analyze_route
from app.config import Settings, get_settings
from app.database import repos
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

NARRATIVE = (
    "During pump maintenance at the pump station, the steam line energy "
    "isolation was NOT verified before work began. Hot steam was released "
    "when the joint was opened."
)

# A model proposal for the steam narrative. potential_consequence is
# deliberately an exposure code: the deterministic layer must recompute it.
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


# --------------------------------------------------------------------- helpers


def _fresh_pipeline() -> AnalysisPipeline:
    """A pipeline instance of our own, so the singleton is never mutated."""
    return AnalysisPipeline(get_ontology(), Settings(
        gemini_api_key="key", gemini_model="gemini-3.8-flash"
    ))


def _install_pipeline(monkeypatch, pipeline, analyses: list) -> None:
    """Route helper under test control, counting every analyze() invocation."""
    original = pipeline.analyze

    def counting_analyze(*args, **kwargs):
        analyses.append(kwargs.get("provider", args[2] if len(args) > 2 else None))
        return original(*args, **kwargs)

    pipeline.analyze = counting_analyze  # type: ignore[method-assign]
    monkeypatch.setattr(analyze_route, "get_pipeline", lambda *a, **k: pipeline)


def _stub_genai(monkeypatch, *, responses):
    """Stub google-genai, returning each queued response in turn.

    ``responses`` is a list of dicts with either ``text`` or ``raises``. The
    index into that list doubles as proof of how many times Gemini was called.
    """
    state = {"calls": 0}

    class _FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeAFCConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeModels:
        def generate_content(self, model=None, contents=None, config=None):
            spec = responses[min(state["calls"], len(responses) - 1)]
            state["calls"] += 1
            if "raises" in spec:
                raise RuntimeError(spec["raises"])
            return SimpleNamespace(text=spec["text"])

    class _FakeClient:
        def __init__(self, api_key=None):
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
    return state


def _ok(*, count: int = 1):
    return [{"text": json.dumps(STEAM_PAYLOAD)} for _ in range(count)]


# ------------------------------------------- 1. exactly one analysis per POST


def test_one_request_performs_exactly_one_analysis(monkeypatch):
    """The route must not analyse the same narrative twice."""
    analyses: list = []
    _install_pipeline(monkeypatch, _fresh_pipeline(), analyses)

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-RULES-1", narrative=NARRATIVE, provider="rules"
        )
    )

    assert res.id
    assert len(analyses) == 1, f"expected 1 analysis, got {len(analyses)}"


def test_one_request_performs_exactly_one_analysis_on_llm_path(monkeypatch):
    analyses: list = []
    pipeline = _fresh_pipeline()
    _install_pipeline(monkeypatch, pipeline, analyses)
    _stub_genai(monkeypatch, responses=_ok())

    analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-LLM-1", narrative=NARRATIVE, provider="llm"
        )
    )

    assert len(analyses) == 1


# ------------------------------- 2. exactly one Gemini extraction invocation


def test_exactly_one_gemini_call_per_request_on_llm_path(monkeypatch):
    """The double-call cost was paid per request; now Gemini is called once."""
    state = _stub_genai(monkeypatch, responses=_ok(count=5))
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-GEM-1", narrative=NARRATIVE, provider="llm"
        )
    )

    assert state["calls"] == 1, f"expected 1 generate_content, got {state['calls']}"


def test_second_call_would_have_been_a_fallback(monkeypatch):
    """Provenance guard.

    If the route analysed twice, the second call would fail and the database
    would hold a rules fallback while the response reported a clean llm run.
    With the fix the queued second response is never reached at all.
    """
    state = _stub_genai(
        monkeypatch,
        responses=[
            {"text": json.dumps(STEAM_PAYLOAD)},
            {"raises": "503 UNAVAILABLE. This model is currently "
                       "experiencing high demand."},
        ],
    )
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-PROV-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    assert state["calls"] == 1, "the second Gemini call must not happen"
    # Response and database agree, and both come from the single llm run.
    assert res.provider == saved.provider == "llm"
    assert res.fallback_used is False and saved.fallback_used is False
    assert res.warnings == [] and saved.fallback_reason == ""
    assert res.event == saved.event.model_dump()


# ----------------------------- 3. response, metadata and persistence agree


def test_persisted_observation_is_the_returned_event(monkeypatch):
    _stub_genai(monkeypatch, responses=_ok())
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-PERSIST-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    assert res.event == saved.event.model_dump()
    assert saved.report_id == res.report_id
    assert saved.narrative == NARRATIVE


def test_provider_metadata_belongs_to_the_single_invocation(monkeypatch):
    _stub_genai(monkeypatch, responses=_ok())
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-META-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    assert res.provider == res.resolved_provider == saved.provider == "llm"
    assert res.requested_provider == saved.requested_provider == "llm"
    assert res.fallback_used == saved.fallback_used is False
    assert res.fallback_reason == saved.fallback_reason == ""


def test_event_identity_is_stable_across_the_whole_chain(monkeypatch):
    """The same event object must be what is returned, saved and re-read."""
    _stub_genai(monkeypatch, responses=_ok())
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-IDENT-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    # Identity, not just equality: the response is built from the saved event.
    assert res.event == saved.event.model_dump()
    assert saved.event.energy == res.event["energy"] == "thermal_energy"
    assert saved.event.barrier_state == res.event["barrier_state"] == "not_verified"
    assert saved.precursor_family_id == res.precursor_family_id


# ------------------------------------------- 4. safety behaviour unchanged


def test_deterministic_fallback_still_works_and_stays_single(monkeypatch):
    """A failing Gemini must still fall back - exactly once, and consistently."""
    state = _stub_genai(monkeypatch, responses=[{"raises": "503 UNAVAILABLE."}])
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-FALL-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    assert state["calls"] == 1
    assert res.provider == res.resolved_provider == saved.provider == "rules"
    assert res.requested_provider == saved.requested_provider == "llm"
    assert res.fallback_used is True and saved.fallback_used is True
    assert res.fallback_reason and saved.fallback_reason
    assert res.warnings
    assert res.event == saved.event.model_dump()
    # Deterministic extraction still produced a complete, correct event.
    assert saved.event.energy == "thermal_energy"
    assert saved.event.barrier_state == "not_verified"


def test_deterministic_consequence_and_sif_still_authoritative(monkeypatch):
    """The model's invalid potential_consequence must still be recomputed."""
    _stub_genai(monkeypatch, responses=_ok())
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-SIF-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    # "thermal_burn" is an exposure code, never a potential_consequence.
    assert res.event["potential_consequence"] != "thermal_burn"
    assert saved.event.potential_consequence == res.event["potential_consequence"]
    assert saved.event.sif.classification == res.event["sif"]["classification"]


def test_evidence_spans_remain_grounded_in_the_narrative(monkeypatch):
    _stub_genai(monkeypatch, responses=_ok())
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-EVID-1", narrative=NARRATIVE, provider="llm"
        )
    )
    saved = repos.get_observation(res.id)

    for key, value in (saved.event.field_evidence or {}).items():
        if value:
            assert value in NARRATIVE, f"{key} not grounded: {value!r}"
    # The response serializes the same spans the observation stores.
    assert [e.model_dump() for e in saved.event.evidence] == res.event["evidence"]


def test_confined_space_extraction_survives_the_single_analysis_change(monkeypatch):
    """The confined-space target fields must be unchanged by this refactor."""
    narrative = (
        "Before entering the storage vessel to inspect its interior, the "
        "maintenance team did not verify that the vessel had been properly "
        "isolated and made safe for entry. The atmosphere was not confirmed "
        "safe, ventilation had not been established, and the worker entered "
        "the vessel without completing the required entry checks."
    )
    _stub_genai(monkeypatch, responses=[{"raises": "503 UNAVAILABLE."}])
    _install_pipeline(monkeypatch, _fresh_pipeline(), [])

    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-CS-1", narrative=narrative, provider="llm"
        )
    )
    ev = res.event

    assert ev["activity"] == "confined_space_entry"
    assert ev["task_phase"] == "inspection"
    assert ev["energy"] == "flammable_atmosphere"
    assert ev["barrier"] == "confined_space_procedure"
    assert ev["barrier_state"] == "not_verified"
    assert ev["exposure"] == "confined_space_atmosphere"
    assert ev["sif"]["classification"] == "high"


# ------------------------------------------- 5. response shape compatibility


def test_response_shape_is_unchanged(monkeypatch):
    """The public AnalyzeResponse contract must not shift."""
    from app.schemas.api import AnalyzeRequest as SchemaReq  # noqa: F401
    from app.schemas.api import AnalyzeResponse

    expected = {
        "id", "report_id", "provider", "resolved_provider", "requested_provider",
        "fallback_used", "fallback_reason", "warnings", "event",
        "precursor_family_id", "document_id", "report_segment_id",
        "segment_index", "report_type",
    }
    assert set(AnalyzeResponse.model_fields) == expected

    _install_pipeline(monkeypatch, _fresh_pipeline(), [])
    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="ONCE-SHAPE-1", narrative=NARRATIVE, provider="rules"
        )
    )
    assert isinstance(res, AnalyzeResponse)
    assert res.report_type == "unknown"
    assert isinstance(res.warnings, list)
    assert isinstance(res.event, dict)


# ------------------------------ 6. to_observation keeps its own single analyse


def test_to_observation_still_analyses_exactly_once(monkeypatch):
    """The legacy helper is unchanged for seed.py and existing callers."""
    state = _stub_genai(monkeypatch, responses=_ok(count=3))
    pipeline = _fresh_pipeline()

    obs = pipeline.to_observation("ONCE-TOOBS-1", NARRATIVE, provider="llm")

    assert state["calls"] == 1
    assert obs.provider == "llm"
    assert obs.event.energy == "thermal_energy"


def test_observation_from_result_reuses_without_reanalysing(monkeypatch):
    """The new helper must not trigger a second extraction."""
    state = _stub_genai(monkeypatch, responses=_ok(count=3))
    pipeline = _fresh_pipeline()

    result = pipeline.analyze("ONCE-REUSE-1", NARRATIVE, provider="llm")
    obs = pipeline.observation_from_result(
        result, "ONCE-REUSE-1", NARRATIVE, report_type="incident"
    )

    assert state["calls"] == 1
    assert obs.event is result.event
    assert obs.provider == result.provider
    assert obs.fallback_used == result.fallback_used
    assert obs.report_type == "incident"
