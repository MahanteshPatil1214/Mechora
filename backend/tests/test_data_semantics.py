"""Data-semantics / consistency regression tests.

1. Verified/compliance (controlled) families are NOT precursor families: they
   are excluded from precursor lists, recurring precursor counts and recurring
   status, while remaining fetchable for validation (hard-negative control).
2. One authoritative recurrence unit (unique observation/report records) is
   used consistently across the family card, detail, recurrence threshold and
   linked observation count — impossible "1 ≥ 2" values never occur.
3. Explicitly verified positive-control narratives with no release never get
   an invented "Uncontrolled Gas Release" exposure.
4. Hard exclusion preserved: verified / not_verified / failed barrier states
   never merge into one family.
"""

from __future__ import annotations

from app.config import get_settings
from app.database import repos
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.services.precursor.engine import PrecursorEngine
from app.services.precursor.family import FamilyBuilder

VERIFIED_NO_RELEASE = (
    "Pipeline maintenance: zero pressure was confirmed and isolation "
    "verified before the joint was opened. No gas was released."
)
VERIFIED_NO_RELEASE_ALT = (
    "Compressor maintenance: lockout was checked and the system proven "
    "depressurized before work. No release occurred."
)
NOT_VERIFIED_RELEASE = (
    "Pipeline maintenance: zero pressure was NOT confirmed before the joint "
    "was opened and gas was released."
)
NOT_VERIFIED_RELEASE_ALT = (
    "Valve maintenance: zero pressure was NOT confirmed before the joint "
    "was opened and gas was released."
)
FAILED_RELEASE = (
    "Pipeline maintenance: the isolation valve failed and ruptured, "
    "releasing gas to atmosphere."
)


def _obs(pipeline, rid, narrative):
    o = pipeline.to_observation(rid, narrative, provider="rules")
    o.id = rid
    return o


def _pipeline():
    return AnalysisPipeline(get_ontology(), get_settings())


# ---------------------------------------------------------------------------
# 1. Controlled (verified) families excluded from precursor surfaces/counts
# ---------------------------------------------------------------------------


def test_controlled_families_excluded_from_precursor_lists_and_counts():
    pipeline = _pipeline()
    obs = [
        _obs(pipeline, "V1", VERIFIED_NO_RELEASE),
        _obs(pipeline, "V2", VERIFIED_NO_RELEASE_ALT),
        _obs(pipeline, "N1", NOT_VERIFIED_RELEASE),
        _obs(pipeline, "N2", NOT_VERIFIED_RELEASE_ALT),
    ]
    for o in obs:
        repos.create_observation(o)

    all_fams = {f.id: f for f in repos.list_families(include_controls=True)}
    controlled = [f for f in all_fams.values() if f.family_type == "controlled"]
    assert controlled, "expected a verified/compliance (controlled) family to exist"
    assert len(controlled) == 1
    control_id = controlled[0].id

    visible = repos.list_families()
    assert visible, "expected precursor families to be visible"
    assert all(f.family_type != "controlled" for f in visible)
    assert control_id not in {f.id for f in visible}

    # still available by id for validation (hard-negative control group)
    fetched = repos.get_family(control_id)
    assert fetched is not None and fetched.family_type == "controlled"

    # dashboard recurring counts exclude controlled families
    summary = repos.dashboard_summary()
    assert summary["precursor_families"] == len(all_fams) - len(controlled)
    recurring_precursor = [
        f for f in all_fams.values()
        if f.family_type != "controlled" and f.recurring
    ]
    assert summary["recurring_precursor_families"] == len(recurring_precursor)
    assert summary["total_observations"] == 4


# ---------------------------------------------------------------------------
# 2. Recurrence unit consistency (never "1 ≥ 2")
# ---------------------------------------------------------------------------


def test_recurrence_unit_consistent_across_surfaces():
    pipeline = _pipeline()
    obs = [
        _obs(pipeline, "N1", NOT_VERIFIED_RELEASE),
        _obs(pipeline, "N2", NOT_VERIFIED_RELEASE_ALT),
        _obs(pipeline, "N3", "Pump maintenance: zero pressure was NOT "
                              "confirmed before the joint was opened and gas "
                              "was released."),
        _obs(pipeline, "H1", "Hot work on a tank: the gas test was skipped "
                             "before grinding started; sparks could ignite "
                             "vapours."),
    ]
    families, _ = PrecursorEngine(get_ontology(), get_settings()).run(obs)

    recurring = [f for f in families if f.recurring]
    assert recurring, "expected a recurring precursor family"
    for f in recurring:
        n = f.recurrence["observation_count"]
        assert n == len(f.observation_ids), "card/detail linked count mismatch"
        assert n >= f.recurring_threshold, f"recurring family with {n} < threshold"
        assert f.recurrence["distinct_report_count"] == n
        assert f.recurrence["distinct_report_count"] <= len(f.observation_ids)
        assert f.recurrence["is_recurring"] is True

    for f in families:
        if not f.recurring:
            assert f.recurrence["observation_count"] < f.recurring_threshold, (
                f"impossible '1 ≥ 2' surface on {f.id}"
            )


def test_recurrence_unit_counts_unique_records_not_duplicates():
    pipeline = _pipeline()
    obs = [
        _obs(pipeline, "DUP", NOT_VERIFIED_RELEASE),
        _obs(pipeline, "DUP", NOT_VERIFIED_RELEASE_ALT),
    ]
    families, _ = FamilyBuilder(get_ontology()).build(
        [[obs[0], obs[1]]], recurring_threshold=2
    )
    fam = families[0]
    assert fam.recurrence["observation_count"] == 1
    assert fam.recurrence["distinct_report_count"] == 1
    assert fam.recurrence["is_recurring"] is False
    assert fam.recurring is False


# ---------------------------------------------------------------------------
# 3. Verified positive control never invents exposure
# ---------------------------------------------------------------------------


def test_verified_positive_control_never_invents_exposure():
    pipeline = _pipeline()
    res = pipeline.analyze("V1", VERIFIED_NO_RELEASE, provider="rules")
    ev = res.event
    assert ev.barrier_state == "verified"
    assert ev.exposure == "unknown"
    assert not ev.field_evidence.get("exposure")
    assert ev.field_basis.get("exposure") == "unknown"
    assert ev.potential_consequence == "unknown"
    assert ev.sif.classification != "high"


def test_llm_path_verified_no_release_extinguishes_invented_exposure():
    from app.models.safety_event import LLMExtraction

    pipeline = _pipeline()
    raw = LLMExtraction(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        energy="pressurized_gas",
        barrier="energy_isolation",
        barrier_state="verified",
        exposure="uncontrolled_gas_release",
        potential_consequence="serious_injury_or_fatality",
        location="pipeline_section",
        life_saving_rules=["energy_isolation"],
        evidence=["isolation was verified"],
        confidence=0.9,
    )
    # An LLM asserting a release that the narrative explicitly negates must be
    # extinguished for a verified positive control.
    ev = pipeline._build_event("V1", VERIFIED_NO_RELEASE, raw, None)
    assert ev.barrier_state == "verified"
    assert ev.exposure == "unknown"
    assert ev.potential_consequence == "unknown"


def test_verified_with_explicitly_grounded_release_keeps_exposure():
    from app.models.safety_event import LLMExtraction

    pipeline = _pipeline()
    narrative = (
        "Pipeline maintenance: isolation was verified, but a flange "
        "leaked and gas was released into the atmosphere."
    )
    raw = LLMExtraction(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        energy="pressurized_gas",
        barrier="energy_isolation",
        barrier_state="verified",
        exposure="uncontrolled_gas_release",
        location="pipeline_section",
        confidence=0.9,
    )
    ev = pipeline._build_event("V2", narrative, raw, None)
    assert ev.barrier_state == "verified"
    assert ev.exposure == "uncontrolled_gas_release"


# ---------------------------------------------------------------------------
# 4. Hard exclusion: verified != not_verified != failed
# ---------------------------------------------------------------------------


def test_verified_not_verified_failed_never_merge():
    pipeline = _pipeline()
    obs = [
        _obs(pipeline, "V1", VERIFIED_NO_RELEASE),
        _obs(pipeline, "N1", NOT_VERIFIED_RELEASE),
        _obs(pipeline, "F1", FAILED_RELEASE),
    ]
    families, assign = PrecursorEngine(get_ontology(), get_settings()).run(obs)
    ids = {assign["V1"], assign["N1"], assign["F1"]}
    assert "UNASSIGNED / PENDING REVIEW" not in ids
    assert len(ids) == 3, "verified / not_verified / failed must never share a family"
    by_id = {f.id: f for f in families}
    assert by_id[assign["V1"]].family_type == "controlled"
    assert by_id[assign["N1"]].common_barrier_state == "not_verified"
    assert by_id[assign["F1"]].common_barrier_state == "failed"