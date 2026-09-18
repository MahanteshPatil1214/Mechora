"""End-to-end pipeline assertions on representative narratives."""

from __future__ import annotations

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

SAMPLES = [
    (
        "During flange maintenance work, no one confirmed zero energy before "
        "the job began; gas was heard leaking from the flange at the pipeline "
        "section. A worker sustained a minor cut.",
        {
            "activity": "pipeline_maintenance",
            "energy": "pressurized_gas",
            "barrier": "energy_isolation",
            "barrier_state": "not_verified",
        },
    ),
    (
        "During hot work in a storage tank, flammable vapour was present and "
        "gas testing had not been completed; a flash fire occurred briefly. "
        "No injury was reported.",
        {
            "activity": "hot_work",
            "energy": "flammable_atmosphere",
            "barrier": "hot_work_controls",
            "barrier_state": "not_verified",
        },
    ),
    (
        "During lifting operations, a suspended load was being moved over "
        "workers; the exclusion zone was not established. "
        "No injury was reported.",
        {
            "activity": "lifting_operations",
            "energy": "gravity",
            "barrier": "lifting_controls",
            "barrier_state": "not_verified",
        },
    ),
    (
        "During pump maintenance on the gas line, the pump was isolated and "
        "locked out before the casing was opened. No injury was reported.",
        {
            "activity": "pump_maintenance",
            "energy": "pressurized_gas",
            "barrier": "energy_isolation",
            "barrier_state": "verified",
        },
    ),
]


def test_analyze_runs_all_providers():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    for narrative, _gt in SAMPLES:
        result = pipeline.analyze("OBS-X", narrative, provider="rules")
        assert result.provider == "rules"
        assert result.event.report_id == "OBS-X"
        assert result.event.narrative == narrative


def test_known_narratives_match_ground_truth_structure():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    for narrative, gt in SAMPLES:
        event = pipeline.analyze("OBS-X", narrative, provider="rules").event
        for field, expected in gt.items():
            assert getattr(event, field) == expected, (narrative, field)


def test_deterministic_same_input_same_output():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    narrative = SAMPLES[0][0]
    a = pipeline.analyze("OBS-1", narrative, provider="rules").event
    b = pipeline.analyze("OBS-2", narrative, provider="rules").event
    assert a.model_dump(exclude={"report_id"}) == b.model_dump(exclude={"report_id"})


def test_schema_is_strict_and_valid():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    event = pipeline.analyze(
        "OBS-1", SAMPLES[1][0], provider="rules"
    ).event
    dumped = event.model_dump()
    assert dumped["barrier_state"] in {
        "verified", "not_verified", "failed", "partially_effective",
        "absent", "unknown",
    }
    assert event.precursor_signature.barrier == event.barrier


def test_verified_and_not_verified_do_not_share_family():
    """PRD 14: differing barrier state where either side is verified
    blocks grouping entirely (structural hard rule)."""
    from app.services.precursor.engine import PrecursorEngine
    from app.services.precursor.similarity import (
        StructuralSimilarity, build_signature,
    )

    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    o1 = pipeline.to_observation("OBS-A",
        "No one confirmed zero pressure before the job began; gas was heard "
        "leaking from the flange.")
    o2 = pipeline.to_observation("OBS-B",
        "Zero pressure was verified before the job began.")
    o1.id, o2.id = "OBS-A", "OBS-B"
    assert o1.event.barrier_state == "not_verified"
    assert o2.event.barrier_state == "verified"

    score = StructuralSimilarity().score(
        build_signature(o1.event), build_signature(o2.event)
    )
    assert score["similarity"] == 0.0, "verified vs non-verified must not group"

    families, assignment = PrecursorEngine(get_ontology(), get_settings()).run(
        [o1, o2]
    )
    assert assignment[o1.id] != assignment[o2.id]
    for fam in families:
        assert not (o1.id in fam.observation_ids and o2.id in fam.observation_ids)


def test_flange_gas_line_maintenance_activity():
    """Regression: real HSE wording must resolve to pipeline_maintenance,
    not unknown (activity was previously unmapped)."""
    narrative = (
        "During routine flange tightening on the gas line, the fitter did "
        "not confirm zero energy before loosening the joint and a small gas "
        "release occurred."
    )
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "OBS-FLG", narrative, provider="rules"
    ).event
    assert event.activity == "pipeline_maintenance"
    assert event.task_phase == "maintenance"
    assert event.energy == "pressurized_gas"
    assert event.barrier == "energy_isolation"
    assert event.barrier_state == "not_verified"
    assert event.exposure == "uncontrolled_gas_release"
    assert event.potential_consequence == "serious_injury_or_fatality"


def test_sif_and_lsr_are_present():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    event = pipeline.analyze("OBS-1", SAMPLES[0][0], provider="rules").event
    assert event.sif.classification in {
        "high", "medium", "low", "needs_review"
    }
    assert event.sif.model_note  # decision-support disclaimer present
    assert isinstance(event.life_saving_rules, list)
    assert event.lsr_mapping.basis


def test_no_invented_consequence_for_unknown_hazard_eval935():
    """Regression: 'Zero energy verification was not carried out.' establishes
    no actual hazard/exposure, so the engine must NOT infer a serious potential
    consequence nor classify SIF as YES simply because a barrier check failed."""
    narrative = "Zero energy verification was not carried out."
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "EVAL-935-RE", narrative, provider="rules"
    ).event
    assert event.energy == "unknown"
    assert event.exposure == "unknown"
    assert event.barrier_state == "not_verified"
    assert event.potential_consequence == "unknown"
    assert event.sif.classification == "needs_review"
    assert event.sif.classification not in ("high", "medium")


def test_sif_evidence_is_grounded_in_narrative_spans():
    """SIF supporting evidence must expose the actual narrative text behind
    critical fields. A rule-inferred potential consequence is clearly labeled
    as model inference and never presented as a fabricated text span."""
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    event = pipeline.analyze("OBS-1", SAMPLES[0][0], provider="rules").event
    evidence_text = " ".join(event.sif.supporting_evidence)
    assert "grounded exposure" in evidence_text
    assert any("leak" in line.lower() for line in event.sif.supporting_evidence)
    assert "potential consequence" in evidence_text
    # Gas-leak narrative never states the consequence -> model inference,
    # no fabricated evidence span allowed.
    assert event.potential_consequence_basis == "model_inference"
    assert not event.field_evidence.get("potential_consequence", "")
    assert "MODEL-INFERRED" in evidence_text


def test_explicit_consequence_binds_evidence_and_basis():
    """When the report literally states a severe potential outcome, the
    consequence is surfaced as explicit with the exact verbatim text attached."""
    narrative = (
        "During flange maintenance work, zero energy was not confirmed before "
        "the job began and gas was heard leaking; this could have been fatal."
    )
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "OBS-EXPL", narrative, provider="rules"
    ).event
    assert event.actual_consequence == "serious_injury_or_fatality"
    assert event.potential_consequence == "serious_injury_or_fatality"
    assert event.potential_consequence_basis == "explicit"
    span = event.field_evidence.get("potential_consequence", "")
    assert span and span in event.narrative
    assert event.sif.basis == "explicit"


def test_non_verbatim_evidence_never_leaks_canonical_text():
    """'zero-energy' in the narrative must produce its EXACT hyphenated span;
    an absent phrase must produce NO evidence (never the canonical synonym)."""
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    ev = pipeline.analyze("OBS-ZE", "Zero-energy was never confirmed before work.",
                          provider="rules").event
    assert ev.barrier == "energy_isolation"
    span = ev.field_evidence.get("barrier", "")
    assert span
    assert span in ev.narrative
    assert span.lower() == "zero-energy"
    ev2 = pipeline.analyze(
        "OBS-NOV", "The flange was opened without any verification.", provider="rules"
    ).event
    assert ev2.field_evidence.get("barrier", "") == ""


def test_full_evidence_spans_and_model_inference_label():
    """Final regression: every extracted field carries its EXACT verbatim
    source span (never 'no direct span' when the text contains it), the
    canonical value stays separate, and the rule-inferred potential
    consequence is visibly labelled MODEL INFERENCE with no fabricated span."""
    narrative = (
        "During compressor maintenance, the isolation was not verified before "
        "work and gas was heard leaking from the flange; a worker sustained a "
        "minor cut."
    )
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "FINAL-REGR", narrative, provider="rules"
    ).event

    assert event.activity == "compressor_maintenance"
    assert event.task_phase == "maintenance"
    assert event.energy == "pressurized_gas"
    assert event.barrier == "energy_isolation"
    assert event.barrier_state == "not_verified"
    assert event.exposure == "uncontrolled_gas_release"
    assert event.actual_consequence == "minor_injury"

    for key in (
        "activity", "task_phase", "energy", "barrier",
        "barrier_state", "exposure", "actual_consequence",
    ):
        span = event.field_evidence.get(key, "")
        assert span, f"missing verbatim evidence for {key}"
        assert span in event.narrative, f"evidence for {key} not verbatim: {span!r}"

    assert event.field_evidence["task_phase"] == "maintenance"

    # Canonical value and evidence stay separate (value is never a span).
    assert event.field_evidence["energy"] != event.energy
    assert event.field_evidence["barrier"] != event.barrier

    # Inferred potential: clearly labelled, never fabricated evidence.
    assert event.potential_consequence == "serious_injury_or_fatality"
    assert event.potential_consequence_basis == "model_inference"
    assert not event.field_evidence.get("potential_consequence", "")
    assert any("MODEL-INFERRED" in l for l in event.sif.supporting_evidence)


def test_failed_state_alone_never_yields_sif_yes():
    """A failed barrier state with no hazard/exposure evidence produces
    needs_review, never an invented high/medium SIF classification."""
    narrative = "Isolation was not verified before the task started."
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "OBS-ISO", narrative, provider="rules"
    ).event
    assert event.barrier_state == "not_verified"
    assert event.sif.classification == "needs_review"
    assert event.sif.classification not in ("high", "medium")
    assert "Insufficient critical evidence" in event.sif.reason