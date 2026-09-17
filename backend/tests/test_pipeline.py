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
        "During pump maintenance, the pump was isolated and locked out "
        "before the casing was opened. No injury was reported.",
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
        "No one confirmed zero energy before the job began.")
    o2 = pipeline.to_observation("OBS-B",
        "Zero energy was confirmed before the job began.")
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


def test_sif_and_lsr_are_present():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    event = pipeline.analyze("OBS-1", SAMPLES[0][0], provider="rules").event
    assert event.sif.classification in {
        "high", "medium", "low", "needs_review"
    }
    assert event.sif.model_note  # decision-support disclaimer present
    assert isinstance(event.life_saving_rules, list)
    assert event.lsr_mapping.basis