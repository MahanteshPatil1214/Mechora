"""Final adversarial / verification suite (audit round 4).

Covers the mandatory adversarial pairs, negation markers (NOT / NO / WITHOUT /
NEVER / FAILED TO / nothing) without false negation, structural grouping rules
(same mechanism -> same family; different barrier / barrier state -> separate;
ambiguous -> NEEDS_REVIEW) and the invariant that the LIVE dashboard and the
evaluation benchmark execute the exact same rule pipeline.
"""

from __future__ import annotations

import inspect
import json
import pathlib
import sys

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.services.negation.engine import NegationEngine

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_evaluation as run_eval_mod  # noqa: E402

PIPELINE = AnalysisPipeline(get_ontology(), get_settings())


def _src(obj) -> str:
    return inspect.getsource(obj)


def _engine():
    from app.services.precursor.engine import PrecursorEngine
    return PrecursorEngine(get_ontology(), get_settings())


def _obs(rid: str, narrative: str):
    o = PIPELINE.to_observation(rid, narrative, provider="rules")
    o.id = rid
    return o


def _run_engine(*narratives):
    """Returns (observations, families, obs_id -> family_id assignment)."""
    obs = [_obs(r, n) for r, n in narratives]
    families, assignment = _engine().run(obs)
    return obs, families, assignment


# ---------------------------------------------------------------------------
# Mandatory adversarial pairs (verbatim narratives from the audit brief)
# ---------------------------------------------------------------------------


def test_mandatory_pair_isolation_verified_vs_not():
    a = PIPELINE.analyze("ADV-A", (
        "Isolation was verified before work began."), provider="rules").event
    b = PIPELINE.analyze("ADV-B", (
        "Isolation was NOT verified before work began."), provider="rules").event
    assert a.barrier_state == "verified"
    assert b.barrier_state == "not_verified"
    _, families, assign = _run_engine(
        ("ADV-A", "Isolation was verified before work began."),
        ("ADV-B", "Isolation was NOT verified before work began."),
    )
    assert not _share_family(assign, "ADV-A", "ADV-B")
    for fam in families:
        members = {m for m in fam.observation_ids if m in ("ADV-A", "ADV-B")}
        assert len(members) != 2


def _share_family(assign, rid_a, rid_b) -> bool:
    fa, fb = assign.get(rid_a), assign.get(rid_b)
    if not fa or not fb:
        return False
    if fa == "UNASSIGNED / PENDING REVIEW" or fb == "UNASSIGNED / PENDING REVIEW":
        return False
    return fa == fb


def test_mandatory_pair_valve_failed_vs_checked():
    c = PIPELINE.analyze("ADV-C", (
        "The valve failed to hold pressure."), provider="rules").event
    d = PIPELINE.analyze("ADV-D", (
        "The valve was checked and held pressure."), provider="rules").event
    assert c.barrier_state == "failed"
    assert d.barrier_state == "verified"
    _, families, assign = _run_engine(
        ("ADV-C", "The valve failed to hold pressure."),
        ("ADV-D", "The valve was checked and held pressure."),
    )
    assert not _share_family(assign, "ADV-C", "ADV-D")


def test_mandatory_pair_zero_pressure_confirmed_vs_not():
    e = PIPELINE.analyze("ADV-E", (
        "Zero pressure was confirmed before maintenance."), provider="rules").event
    f = PIPELINE.analyze("ADV-F", (
        "Zero pressure was NOT confirmed before maintenance."), provider="rules").event
    assert e.barrier_state == "verified"
    assert f.barrier_state == "not_verified"
    _, families, assign = _run_engine(
        ("ADV-E", "Zero pressure was confirmed before maintenance."),
        ("ADV-F", "Zero pressure was NOT confirmed before maintenance."),
    )
    assert not _share_family(assign, "ADV-E", "ADV-F")


# ---------------------------------------------------------------------------
# Negation markers WITHOUT false negation
# ---------------------------------------------------------------------------


def test_negation_markers_no_false_reversal():
    eng = NegationEngine(get_ontology())
    positive_outcomes = [
        "no gas was released during the work",
        "no leak was observed after the test",
        "nothing at all was released",
        "without any release of gas",
        "nothing was released during the job",
        "no pressure was released when the joint was opened",
        "Isolation was verified and no gas was released before flange work",
    ]
    for text in positive_outcomes:
        assert eng.classify_sentence(text).state == "verified", text

    true_negations = [
        "The permit was not approved.",
        "No permit was issued for entry.",
        "The team failed to verify zero energy.",
        "Work commenced without verifying isolation.",
        "Zero pressure was NEVER confirmed before startup.",
        "The worker never confirmed the isolation.",
        "The line was NOT verified as depressurized.",
        "Depressurization could not be confirmed.",
        "The work started without the isolation being verified.",
        "Zero energy was not confirmed before the valve was opened.",
    ]
    for text in true_negations:
        state = eng.classify_sentence(text).state
        assert state in ("not_verified", "unknown"), text


def test_negation_positive_outcome_not_labeled_not_verified():
    narrative = (
        "Zero pressure was confirmed and the isolation held with no gas "
        "released during maintenance."
    )
    event = PIPELINE.analyze("ADV-N1", narrative, provider="rules").event
    assert event.barrier_state == "verified"
    assert event.precursor_signature.barrier_state == "verified"


# ---------------------------------------------------------------------------
# Structural grouping rules (live engine)
# ---------------------------------------------------------------------------


def test_same_mechanism_different_equipment_same_family():
    _, families, assign = _run_engine(
        ("ADV-P1", "Isolation valve failed and gas escaped during maintenance."),
        ("ADV-P3", "The pump discharge valve failed and gas leaked out."),
    )
    assert assign["ADV-P1"] == assign["ADV-P3"]
    fam = next(f for f in families if f.id == assign["ADV-P1"])
    assert fam.common_barrier == "energy_isolation"
    assert fam.common_barrier_state == "failed"


def test_different_barrier_different_family():
    _, families, assign = _run_engine(
        ("ADV-P1", "Isolation valve failed and gas escaped during maintenance."),
        ("ADV-Q1", "Work permit was not approved and gas escaped during hot work."),
    )
    assert not _share_family(assign, "ADV-P1", "ADV-Q1")
    fams = {f.id: f for f in families}
    assert fams[assign["ADV-P1"]].common_barrier == "energy_isolation"
    assert fams[assign["ADV-Q1"]].common_barrier == "work_permit"


def test_different_barrier_state_never_shared_family():
    _, families, assign = _run_engine(
        ("ADV-N1", (
            "Zero pressure was confirmed and the isolation held with no gas "
            "released during maintenance.")),
        ("ADV-N2", (
            "Zero pressure was NOT confirmed and gas was released from the "
            "drain valve during maintenance.")),
    )
    assert not _share_family(assign, "ADV-N1", "ADV-N2")
    fams = {f.id: f for f in families}
    assert fams[assign["ADV-N1"]].common_barrier_state == "verified"
    assert fams[assign["ADV-N1"]].family_type == "controlled"
    assert fams[assign["ADV-N2"]].common_barrier_state == "not_verified"


def test_ambiguous_and_missing_critical_needs_review():
    _, _, assign = _run_engine(
        ("ADV-AMB", "Some work was done yesterday."),
        ("ADV-AMB2", "A valve on the line was inspected by the crew."),
    )
    assert assign["ADV-AMB"] == "UNASSIGNED / PENDING REVIEW"
    assert assign["ADV-AMB2"] == "UNASSIGNED / PENDING REVIEW"
    event = PIPELINE.analyze("ADV-AMB", (
        "Some work was done yesterday."), provider="rules").event
    assert event.needs_review is True


def test_equipment_variants_share_same_family_without_false_grouping():
    # Regression guard: four equipment variants of the same failed mechanism
    # must share one family while a verified check stays separate.
    _, families, assign = _run_engine(
        ("EQ-PIPE", ("Pipeline flange maintenance: fitter did not confirm zero "
                     "energy before loosening joint; gas escaped.")),
        ("EQ-PUMP", ("Pump maintenance near transfer station: technician opened "
                     "pump casing without isolation verification; gas release "
                     "occurred.")),
        ("EQ-VALVE", ("Valve replacement on fuel line: zero energy was never "
                      "checked before opening joint; residual gas leaked.")),
        ("EQ-COMP", ("Compressor servicing in unit 3: crew opened casing without "
                     "zero-pressure verification; gas was released.")),
        ("EQ-SAFE", ("Pipeline valve replacement: zero pressure was verified, "
                     "lockout applied, permit signed.")),
    )
    notver_fams = {assign[r] for r in ("EQ-PIPE", "EQ-PUMP", "EQ-VALVE", "EQ-COMP")}
    assert notver_fams == {assign["EQ-PIPE"]}
    assert assign["EQ-SAFE"] != assign["EQ-PIPE"]
    fams = {f.id: f for f in families}
    for r in ("EQ-PIPE", "EQ-PUMP", "EQ-VALVE", "EQ-COMP"):
        assert fams[assign[r]].common_barrier_state == "not_verified"
    assert fams[assign["EQ-SAFE"]].common_barrier_state == "verified"


# ---------------------------------------------------------------------------
# Live dashboard vs evaluation benchmark consistency (no metric fabrication)
# ---------------------------------------------------------------------------


def test_live_and_evaluation_share_same_rule_pipeline():
    from app.api.routes import analyze as analyze_route
    from app.database import repos
    assert "AnalysisPipeline" in _src(analyze_route)
    assert "AnalysisPipeline" in _src(run_eval_mod)
    assert "PrecursorEngine" in _src(repos)


def test_live_prediction_equals_eval_helpers_on_frozen_records():
    """The benchmark's predicted rows must be derived from the exact same
    canonical event the live dashboard renders (no separate scoring path)."""
    doc = json.loads(get_settings().eval_set_path.read_text(encoding="utf-8"))
    sample = [r for r in doc["records"]
              if r["category"] in ("negation", "hard_negative")][:8]
    assert sample

    fields = ("activity", "energy", "barrier", "barrier_state", "exposure",
              "potential_consequence")
    for rec in sample:
        event = PIPELINE.analyze(
            rec["report_id"], rec["narrative"], provider="rules"
        ).event
        dump = event.model_dump()
        for field in fields:
            live = run_eval_mod.pred_field(event, field)
            canonical = str(dump.get(field) or "unknown")
            assert live == canonical, (rec["report_id"], field, live, canonical)

    # Barrier state on negation/hard_negative records is the hard invariant
    # and must match the frozen ground truth live.
    for rec in sample:
        event = PIPELINE.analyze(
            rec["report_id"], rec["narrative"], provider="rules"
        ).event
        gt = str(rec["ground_truth"].get("barrier_state", "unknown") or "unknown")
        assert event.barrier_state == gt, (
            f"{rec['report_id']} live={event.barrier_state} gt={gt} "
            f"narr={rec['narrative']!r}"
        )


def test_live_family_tag_matches_eval_grouping_helper():
    event = PIPELINE.analyze(
        "ADV-N2",
        "Zero pressure was NOT confirmed and gas was released from the "
        "drain valve during maintenance.",
        provider="rules",
    ).event
    tag = run_eval_mod.predicted_family_tag(event)
    assert tag == "energy_isolation::not_verified"


def test_eval_set_has_no_could_not_phrase_regression_door():
    # The inability clause must never silently flip frozen eval records.
    doc = json.loads(get_settings().eval_set_path.read_text(encoding="utf-8"))
    phrases = ("could not", "couldn't", "unable to")
    offenders = [
        r["report_id"] for r in doc["records"]
        if any(p in r["narrative"].lower() for p in phrases)
    ]
    assert not offenders, offenders