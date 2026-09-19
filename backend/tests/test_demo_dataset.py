"""Regression tests for the curated SIH demo dataset & demo hardening.

The final demo dataset must load deterministically, produce exactly the
expected precursor-family structure, keep VERIFIED controls and FAILED
barriers distinct from the NOT_VERIFIED recurring family, and never let the
excluded NON-REPORT footer contaminate observations or evidence. These tests
are run with the deterministic rules provider (pinned in conftest).
"""

from __future__ import annotations

from app.config import get_settings
from app.database import repos
from app.services.demo.seed import (
    DEMO_DATASET_PATH,
    curated_documents,
    reset_demo,
    seed_curated_demo,
)
from app.services.document_segmentation.segmenter import ReportSegmenter
from app.services.pipeline import AnalysisPipeline
from app.services.normalization.ontology import get_ontology

_PIPELINE = AnalysisPipeline(get_ontology(), get_settings())


def _analysis(segment_id: str):
    doc = next(d for d in curated_documents() if d["report_segment_id"] == segment_id)
    return _PIPELINE.analyze(doc["report_id"], doc["text"], provider="rules")


def test_demo_dataset_exactly_seven_report_segments():
    docs = curated_documents()
    assert len(docs) == 7
    assert [d["document_id"] for d in docs] == ["DEMO-CURATED"] * 7
    assert [d["report_segment_id"] for d in docs] == [
        f"DEMO-CURATED-SEG{i}" for i in range(1, 8)
    ]


def test_demo_dataset_excludes_non_report_footer():
    text = DEMO_DATASET_PATH.read_text(encoding="utf-8")
    assert "NON-REPORT" in text
    assert "Expected Test Signals" in text
    for doc in curated_documents():
        assert "NON-REPORT" not in doc["text"]
        assert "Expected Test Signals" not in doc["text"]
        assert "instructions" not in doc["text"]


def test_report1_activity_is_pipeline_maintenance_with_gas_pipeline_evidence():
    ev = _analysis("DEMO-CURATED-SEG1").event
    assert ev.activity == "pipeline_maintenance"
    assert ev.field_evidence.get("activity") == "gas pipeline"
    assert ev.energy == "pressurized_gas"
    assert ev.barrier_state == "not_verified"


def test_report2_barrier_evidence_is_full_verification_clause():
    ev = _analysis("DEMO-CURATED-SEG2").event
    assert ev.barrier == "energy_isolation"
    assert ev.field_evidence.get("barrier") == (
        "before confirming complete isolation of the pressurized gas line"
    )


def test_report2_and_report4_stay_not_verified():
    for seg in ("DEMO-CURATED-SEG2", "DEMO-CURATED-SEG4"):
        ev = _analysis(seg).event
        assert ev.barrier_state == "not_verified"
        assert ev.energy == "pressurized_gas"
        assert ev.barrier == "energy_isolation"


def test_report4_barrier_evidence_is_before_verifying_zero_energy():
    ev = _analysis("DEMO-CURATED-SEG4").event
    assert ev.field_evidence.get("barrier") == "before verifying zero energy"


def test_report7_was_not_effective_is_failed_not_not_verified():
    ev = _analysis("DEMO-CURATED-SEG7").event
    assert ev.barrier_state == "failed"
    assert "was not effective" in ev.field_evidence.get("barrier_state", "")


def test_report5_liquid_incident_stays_separate_mechanism():
    ev = _analysis("DEMO-CURATED-SEG5").event
    assert ev.activity == "pump_maintenance"
    assert ev.energy == "pressurized_liquid"
    assert ev.exposure == "uncontrolled_liquid_release"
    assert ev.field_evidence.get("barrier") == (
        "before cracking the bleeder needle valve to confirm depressurization"
    )
    assert ev.field_evidence.get("actual_consequence") == (
        "No injury occurred and no medical treatment was required."
    )


def test_report6_verified_control_negated_outcome_never_becomes_release():
    ev = _analysis("DEMO-CURATED-SEG6").event
    assert ev.barrier_state == "verified"
    assert ev.exposure == "unknown"
    assert ev.potential_consequence == "unknown"
    for span in ev.field_evidence.values():
        assert "release occurred" not in span


def _seeded():
    result = seed_curated_demo(get_settings())
    obs = repos.all_observations_ordered()
    by_report = {o.report_id: o for o in obs}
    by_obs = {o.id: o.report_id for o in obs}
    families = repos.list_families(limit=100, include_controls=True)
    return result, obs, by_report, by_obs, families


def test_demo_seed_family_structure_exactly_as_expected():
    _result, _obs, by_report, by_obs, families = _seeded()
    by_id = {f.id: f for f in families}

    recurring = [f for f in families if f.recurring]
    controlled = [f for f in families if f.family_type == "controlled"]
    failed = [f for f in families
              if f.common_barrier_state == "failed"]
    liquid = [f for f in families
              if f.common_exposure == "uncontrolled_liquid_release"]

    assert len(recurring) == 1
    gas_fam = recurring[0]
    assert gas_fam.attention_signal > 50
    member_reports = {
        by_obs[obs_id].replace("DEMO-CURATED-SEG", "SEG")
        if obs_id in by_obs else obs_id
        for obs_id in gas_fam.observation_ids
    }
    assert member_reports == {"SEG1", "SEG2", "SEG3", "SEG4"}

    assert len(controlled) == 1
    assert controlled[0].common_barrier_state == "verified"
    ctrl_members = {by_obs[oid] for oid in controlled[0].observation_ids}
    assert ctrl_members == {"DEMO-CURATED-SEG6"}

    assert len(failed) == 1
    assert failed[0].common_barrier_state == "failed"
    fail_members = {by_obs[oid] for oid in failed[0].observation_ids}
    assert fail_members == {"DEMO-CURATED-SEG7"}

    assert len(liquid) == 1
    assert liquid[0].common_exposure == "uncontrolled_liquid_release"

    assert {f.id for f in families} == {
        "PFAM-A7CC6", "PFAM-781A4", "PFAM-F36C4", "PFAM-418BD"
    }


def test_reseed_is_idempotent():
    _a, obs_a, _ra, _ba, fam_a = _seeded()
    obs_ids_a = [o.id for o in obs_a]
    fam_ids_a = sorted(f.id for f in fam_a)
    _b, obs_b, _rb, _bb, fam_b = _seeded()
    obs_ids_b = [o.id for o in obs_b]
    fam_ids_b = sorted(f.id for f in fam_b)
    assert obs_ids_a == obs_ids_b
    assert fam_ids_a == fam_ids_b


def test_reset_clears_observations_and_families():
    _seeded()
    assert repos.count_observations() == 7
    reset_demo()
    assert repos.count_observations() == 0
    assert repos.list_families(limit=100, include_controls=True) == []
    summary = repos.dashboard_summary()
    assert summary["precursor_families"] == 0
    assert summary["recurring_precursor_families"] == 0


def test_demo_upload_path_parity():
    text = DEMO_DATASET_PATH.read_text(encoding="utf-8")
    segs = ReportSegmenter().segment(text)
    reports = [s for s in segs if s.kind == "report"]
    non_reports = [s for s in segs if s.kind != "report"]
    assert len(reports) == 7
    assert len(non_reports) == 1
    assert "NON-REPORT" in non_reports[0].heading.upper()
    assert "Expected Test Signals" in non_reports[0].text