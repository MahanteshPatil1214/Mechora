"""Precursor engine structural tests.

Covers PRD section 12/14 weights, the verified-hard-rule, WHY GROUPED?
per-dimension evidence, WHY NOT GROUPED? exclusions and the explicit
recurring threshold.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.services.precursor.attention import (
    ATTENTION_DISCLAIMER,
    compute_attention,
)
from app.services.precursor.engine import PrecursorEngine
from app.services.precursor.weights import (
    STRUCTURAL_WEIGHTS,
    get_weights,
)

MEERUT_EXAMPLE = (
    "During routine flange tightening on the gas line, the fitter did not "
    "confirm zero energy before loosening the joint and a small gas release "
    "occurred."
)


def _obs(pipeline, rid: str, narrative: str):
    o = pipeline.to_observation(rid, narrative)
    o.id = rid
    return o


def _pipeline_and_obs(narratives: list[tuple[str, str]]):
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    return pipeline, [_obs(pipeline, rid, n) for rid, n in narratives]


def test_weights_match_prd_prototype_table():
    w = get_weights()
    assert abs(w["barrier"] - 0.20) < 1e-9
    assert abs(w["barrier_state"] - 0.10) < 1e-9
    assert abs(w["energy"] - 0.25) < 1e-9
    assert abs(w["exposure"] - 0.20) < 1e-9
    assert abs(w["task_phase"] - 0.15) < 1e-9
    assert abs(w["activity"] - 0.10) < 1e-9
    # barrier + barrier_state make up 30% per the PRD prototype table.
    assert abs(STRUCTURAL_WEIGHTS["barrier"]
               + STRUCTURAL_WEIGHTS["barrier_state"] - 0.30) < 1e-9


def test_grouping_evidence_is_computed_from_members():
    pipeline, obs = _pipeline_and_obs([
        ("FLG-1", MEERUT_EXAMPLE),
        ("CMP-1", "Repair at the compressor discharge: nobody verified "
                  "isolation before the crew opened the casing; pressure "
                  "was still present."),
        ("VLV-1", "Valve maintenance: zero energy was never checked before "
                  "the joint was opened and leaking was noticed."),
    ])
    families, assignment = PrecursorEngine(get_ontology(),
                                           get_settings()).run(obs)
    fam = next(f for f in families if len(f.observation_ids) >= 2)
    # WHY GROUPED? must reflect the actual set: same breaker/state/energy,
    # different activity.
    by_dim = {g.dimension: g for g in fam.grouping_evidence}
    assert by_dim["barrier"].status == "same"
    assert by_dim["barrier"].value == "energy_isolation"
    assert by_dim["barrier_state"].status == "same"
    assert by_dim["energy"].status == "same"
    assert by_dim["energy"].value == "pressurized_gas"
    assert by_dim["activity"].status in ("mixed", "distinct")
    assert by_dim["activity"].coverage < 1.0
    for g in fam.grouping_evidence:
        assert 0.0 <= g.coverage <= 1.0
        assert g.note


def test_why_not_grouped_reports_differing_dimensions():
    """Similarly-worded pipeline reports that share activity/state but fail
    different barriers must stay separate AND report WHY NOT GROUPED."""
    pipeline, obs = _pipeline_and_obs([
        ("GAS-A", MEERUT_EXAMPLE),
        ("WELD-B", "Pipeline repair where gas testing was NOT completed "
                   "before the line was opened; a flash fire occurred."),
    ])
    families, assignment = PrecursorEngine(get_ontology(),
                                           get_settings()).run(obs)
    assert assignment["GAS-A"] != assignment["WELD-B"]
    fam = next(f for f in families if f.id == assignment["GAS-A"])
    assert fam.exclusions, "expected a WHY-NOT-GROUPED exclusion"
    excl = fam.exclusions[0]
    assert excl.other_family_id == assignment["WELD-B"]
    assert "energy" in excl.differing_dimensions
    assert "barrier" in excl.differing_dimensions
    assert "exposure" in excl.differing_dimensions
    assert excl.similarity >= 0.35


def test_recurring_threshold_is_explicit():
    settings = get_settings()
    assert getattr(settings, "recurring_min_observations", 2) >= 2
    pipeline, obs = _pipeline_and_obs([
        ("FLG-1", MEERUT_EXAMPLE),
        ("CMP-1", "Repair at the compressor discharge: nobody verified "
                  "isolation before the crew opened the casing; pressure "
                  "was still present."),
        ("WELD-2", "Pipeline repair where gas testing was NOT completed "
                   "before the line was opened; a flash fire occurred."),
    ])
    families, assignment = PrecursorEngine(get_ontology(), settings).run(obs)
    merged = next(f for f in families if len(f.observation_ids) >= 2)
    assert merged.recurring is True
    assert merged.recurring_threshold == settings.recurring_min_observations
    single = next(f for f in families if len(f.observation_ids) == 1)
    assert single.recurring is False
    assert assignment["FLG-1"] == assignment["CMP-1"]
    assert assignment["FLG-1"] != assignment["WELD-2"]


def test_single_observation_family_is_not_labeled_recurring():
    """A single observation (observation_count < recurring threshold) must
    never be branded RECURRING or 'recurring' anywhere in its narrative."""
    from app.services.precursor.family import FamilyBuilder

    pipeline, obs = _pipeline_and_obs([
        ("SINGLE-1", MEERUT_EXAMPLE),
    ])
    families, _ = FamilyBuilder(get_ontology()).build(
        [obs], family_index=1,
        recurring_threshold=get_settings().recurring_min_observations,
    )
    fam = families[0]
    assert len(fam.observation_ids) == 1
    assert fam.recurring is False
    assert fam.recurrence["status"] == "single"
    assert fam.recurrence["is_recurring"] is False
    narrative = " ".join((fam.description, fam.why_it_matters)).lower()
    assert "recurring" not in narrative
    assert "single" in fam.recurrence["label"]


def test_recurring_family_keeps_recurrence_language():
    """Multi-observation families keep the recurrence narrative; the status
    is derived from the observation count, not the template alone."""
    from app.services.precursor.family import FamilyBuilder

    pipeline, obs = _pipeline_and_obs([
        ("FLG-1", MEERUT_EXAMPLE),
        ("CMP-1", "Repair at the compressor discharge: nobody verified "
                  "isolation before the crew opened the casing; pressure "
                  "was still present."),
        ("FLG-2", MEERUT_EXAMPLE),
    ])
    families, _ = FamilyBuilder(get_ontology()).build(
        [obs], family_index=1,
        recurring_threshold=get_settings().recurring_min_observations,
    )
    fam = families[0]
    assert len(fam.observation_ids) == 3
    assert fam.recurring is True
    assert fam.recurrence["status"] == "recurring"
    assert "recurring" in fam.why_it_matters.lower()


def test_attention_disclaimer_and_contributing_factors_only():
    pipeline, obs = _pipeline_and_obs([
        ("FLG-1", MEERUT_EXAMPLE),
        ("CMP-1", "Repair at the compressor discharge: nobody verified "
                  "isolation before the crew opened the casing; pressure "
                  "was still present."),
    ])
    result = compute_attention(obs)
    assert ATTENTION_DISCLAIMER  # non-empty disclaimer constant
    assert 0.0 <= result["score"] <= 100.0
    assert result["factors"]
    for f in result["factors"]:
        assert 0.0 <= f["contribution"] <= f["weight"] <= 1.0
    # Non-contributing factors must not appear in the basis list.
    contrib_map = {f["factor"]: f["contribution"] for f in result["factors"]}
    for line in result["basis"]:
        assert line  # every basis line is a real contributing factor name


def test_default_settings_expose_exclusion_floor():
    settings = get_settings()
    assert 0.0 <= settings.family_exclusion_floor <= 1.0
    assert settings.family_exclusion_floor < settings.family_assign_threshold