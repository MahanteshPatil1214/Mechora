"""Comprehensive tests for structural precursor mechanisms and safety reasoning.

Validates the 8 core MECHORA requirements:
1. Different wording / same mechanism -> SAME family.
2. Different equipment (pipeline, pump, valve, compressor) / same mechanism -> SAME family.
3. Verified vs not_verified -> STRICTLY SEPARATE families.
4. Failed vs not_verified -> STRICTLY SEPARATE families.
5. Different barriers -> STRICTLY SEPARATE families.
6. Missing critical fields -> NEEDS_REVIEW = True.
7. Negation hard cases:
   - "Isolation was verified" != "Isolation was NOT verified"
   - "Isolation was not verified" != "Isolation failed"
   - "Lockout was checked" != "Lockout was skipped"
8. Ambiguous narratives -> held for review.
9. False grouping prevention -> surface word overlap without mechanism match cannot cluster.
10. False separation prevention -> activity/equipment differences alone cannot split mechanism.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.services.precursor.engine import PrecursorEngine


@pytest.fixture
def pipeline():
    return AnalysisPipeline(get_ontology(), get_settings())


@pytest.fixture
def engine():
    return PrecursorEngine(get_ontology(), get_settings())


def _obs(pipeline, rid: str, narrative: str):
    o = pipeline.to_observation(rid, narrative)
    o.id = rid
    return o


# ---------------------------------------------------------------------------
# 1. Different wording, same mechanism -> SAME family
# ---------------------------------------------------------------------------


def test_different_wording_same_mechanism(pipeline, engine):
    """Different phrasings describing unverified energy isolation must cluster together."""
    narratives = [
        ("W1", "During flange repair, the fitter opened the drain before the line was proven depressurized; residual pressure blew fluid out."),
        ("W2", "Line break started without zero-energy verification; isolation was never confirmed and gas hissed from the flange."),
        ("W3", "Depressurization check was omitted by the crew prior to loosening the joint; hydrocarbon gas leaked out."),
        ("W4", "Technician skipped confirming zero pressure before unbolting the line, causing a sudden gas release."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    # All 4 observations must group into the exact same family
    assigned_family_ids = {assignment[rid] for rid, _ in narratives}
    assert len(assigned_family_ids) == 1, f"Expected 1 family for same mechanism, got: {assigned_family_ids}"

    fam = next(f for f in families if f.id == list(assigned_family_ids)[0])
    assert fam.common_barrier == "energy_isolation"
    assert fam.common_barrier_state == "not_verified"
    assert fam.recurring is True
    assert len(fam.observation_ids) == 4


# ---------------------------------------------------------------------------
# 2. Different equipment, same mechanism -> SAME family
# ---------------------------------------------------------------------------


def test_different_equipment_same_mechanism(pipeline, engine):
    """Pipeline, pump, valve, and compressor maintenance must share the same family

    when the underlying failed barrier is energy isolation.
    """
    narratives = [
        ("EQ-PIPE", "Pipeline flange maintenance: fitter did not confirm zero energy before loosening joint; gas escaped."),
        ("EQ-PUMP", "Pump maintenance near transfer station: technician opened pump casing without isolation verification; gas release occurred."),
        ("EQ-VALVE", "Valve replacement on fuel line: zero energy was never checked before opening joint; residual gas leaked."),
        ("EQ-COMP", "Compressor servicing in unit 3: crew opened casing without zero-pressure verification; gas was released."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    assigned_families = {assignment[rid] for rid, _ in narratives}
    assert len(assigned_families) == 1, (
        f"Pipeline, pump, valve, and compressor maintenance must share family! Got {assigned_families}"
    )

    fam = next(f for f in families if f.id == list(assigned_families)[0])
    assert fam.common_barrier == "energy_isolation"
    assert fam.common_barrier_state == "not_verified"
    assert fam.recurring is True
    assert len(fam.observation_ids) == 4


# ---------------------------------------------------------------------------
# 3. Verified vs Not Verified -> STRICTLY SEPARATE families
# ---------------------------------------------------------------------------


def test_verified_vs_not_verified_separate(pipeline, engine):
    """Energy Isolation Verified must NEVER share a family with Energy Isolation Verification Failure."""
    narratives = [
        ("NOT_VER-1", "Pipeline maintenance: isolation was not verified before opening the line; gas released."),
        ("NOT_VER-2", "Pump repair: zero energy was never checked before dismantling; pressure escaped."),
        ("VER-1", "Pipeline maintenance: zero pressure was verified and isolation confirmed before work started."),
        ("VER-2", "Pump repair: lockout was checked and zero pressure confirmed before opening the pump."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    # NOT_VER and VER must be in completely separate families
    assert assignment["NOT_VER-1"] == assignment["NOT_VER-2"]
    assert assignment["VER-1"] == assignment["VER-2"]
    assert assignment["NOT_VER-1"] != assignment["VER-1"]

    fam_not_ver = next(f for f in families if f.id == assignment["NOT_VER-1"])
    fam_ver = next(f for f in families if f.id == assignment["VER-1"])

    assert fam_not_ver.common_barrier_state == "not_verified"
    assert fam_ver.common_barrier_state == "verified"

    # Must document exclusion / why not grouped
    assert any(ex.other_family_id == fam_ver.id for ex in fam_not_ver.exclusions)


# ---------------------------------------------------------------------------
# 4. Failed vs Not Verified -> STRICTLY SEPARATE families
# ---------------------------------------------------------------------------


def test_failed_vs_not_verified_separate(pipeline, engine):
    """Mechanical barrier failure (valve ruptured) must NOT merge with procedural omission (not verified)."""
    narratives = [
        ("PROC-1", "Technician opened the crude flange without verifying zero energy; gas leaked out."),
        ("PROC-2", "Zero-energy confirmation was skipped before opening the valve manifold; pressure escaped."),
        ("MECH-1", "High-pressure isolation valve ruptured and failed to hold pressure during maintenance, gas escaped."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    assert assignment["PROC-1"] == assignment["PROC-2"]
    assert assignment["PROC-1"] != assignment["MECH-1"]

    fam_proc = next(f for f in families if f.id == assignment["PROC-1"])
    fam_mech = next(f for f in families if f.id == assignment["MECH-1"])

    assert fam_proc.common_barrier_state == "not_verified"
    assert fam_mech.common_barrier_state == "failed"


# ---------------------------------------------------------------------------
# 5. Different barriers -> STRICTLY SEPARATE families
# ---------------------------------------------------------------------------


def test_different_barriers_separate(pipeline, engine):
    """Energy isolation vs hot work controls vs confined space must never merge."""
    narratives = [
        ("ISOL-1", "Flange maintenance on gas line: zero energy was not verified before unbolting; gas leak."),
        ("HOTW-1", "Grinding near storage tank: gas testing was skipped before hot work started; sparks flew."),
        ("CONF-1", "Vessel entry: atmospheric test was not performed prior to tank entry."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    # All three must have different family IDs
    ids = {assignment[rid] for rid, _ in narratives}
    assert len(ids) == 3, f"Expected 3 distinct families for 3 distinct barriers, got {ids}"


# ---------------------------------------------------------------------------
# 6. Missing critical fields -> NEEDS_REVIEW = True
# ---------------------------------------------------------------------------


def test_missing_critical_fields_needs_review(pipeline):
    """An observation lacking critical fields must be flagged for HSE review."""
    vague_text = "The supervisor had a general discussion about site housekeeping during the morning tea break."
    obs = pipeline.to_observation("VAGUE-01", vague_text)

    assert obs.event.needs_review is True
    assert len(obs.event.missing_fields) > 0
    assert "barrier" in obs.event.missing_fields or "energy" in obs.event.missing_fields


# ---------------------------------------------------------------------------
# 7. Negation hard cases
# ---------------------------------------------------------------------------


def test_negation_hard_cases(pipeline):
    """Strict syntactic negation pairs must be classified into exact opposite states."""
    ontology = get_ontology()
    negation = pipeline.negation

    # Pair 1: verified vs not verified
    res_pos = negation.classify_sentence("Isolation was verified before work started.")
    res_neg = negation.classify_sentence("Isolation was NOT verified before work started.")
    assert res_pos.state == "verified"
    assert res_neg.state == "not_verified"

    # Pair 2: checked vs skipped
    res_chk = negation.classify_sentence("Lockout was checked by the lead operator.")
    res_skp = negation.classify_sentence("Lockout was skipped by the lead operator.")
    assert res_chk.state == "verified"
    assert res_skp.state == "not_verified"

    # Pair 3: failure vs not verified
    res_fail = negation.classify_sentence("The isolation valve failed under operating pressure.")
    res_unver = negation.classify_sentence("The isolation valve was not verified before opening.")
    assert res_fail.state == "failed"
    assert res_unver.state == "not_verified"

    # Pair 4: failed to verify -> not_verified (procedural failure)
    res_ftv = negation.classify_sentence("The mechanic failed to verify zero pressure.")
    assert res_ftv.state == "not_verified"


# ---------------------------------------------------------------------------
# 8. Ambiguous narratives -> held for review, no invented consequence
# ---------------------------------------------------------------------------


def test_ambiguous_narratives_no_invented_consequence(pipeline):
    """Observations with insufficient evidence must yield unknown potential consequence."""
    narrative = "Safety officer conducted routine walkaround near compressor shelter."
    obs = pipeline.to_observation("AMBIG-01", narrative)

    assert obs.event.needs_review is True
    assert obs.event.potential_consequence == "unknown"
    assert obs.event.sif.classification == "needs_review"


# ---------------------------------------------------------------------------
# 9. False grouping prevention
# ---------------------------------------------------------------------------


def test_false_grouping_prevention(pipeline, engine):
    """Observations that mention similar words (pipeline, valve) but represent

    different mechanisms must NOT be clustered together.
    """
    narratives = [
        ("SAFE-01", "Pipeline valve replacement: zero pressure was verified, lockout applied, permit signed."),
        ("UNSAFE-01", "Pipeline valve replacement: zero energy was never confirmed, residual gas escaped."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    assert assignment["SAFE-01"] != assignment["UNSAFE-01"], (
        "Verified observation must not falsely group with unverified failure observation!"
    )


# ---------------------------------------------------------------------------
# 10. False separation prevention
# ---------------------------------------------------------------------------


def test_false_separation_prevention(pipeline, engine):
    """Observations occurring in different locations and with different wording

    describing the same precursor mechanism must NOT be separated.
    """
    narratives = [
        ("LOC-A", "Well site 4: zero energy was not checked before the crude flange was unbolted; gas leaked."),
        ("LOC-B", "Offshore platform pump room: nobody verified isolation before the pump was opened; gas leaked."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    assert assignment["LOC-A"] == assignment["LOC-B"], (
        "Same precursor mechanism across different sites/locations must group together!"
    )


# ---------------------------------------------------------------------------
# 11. Why not grouped mechanism explanation
# ---------------------------------------------------------------------------


def test_why_not_grouped_explanation(pipeline, engine):
    """Exclusions must clearly display the differing dimension and separation reason."""
    narratives = [
        ("ISOL-A", "Pipeline flange maintenance: zero energy was not verified before unbolting; gas leak."),
        ("HOTW-A", "Pipeline repair: gas testing was not completed before grinding began; spark ignited vapor."),
    ]
    obs_list = [_obs(pipeline, rid, text) for rid, text in narratives]
    families, assignment = engine.run(obs_list)

    assert assignment["ISOL-A"] != assignment["HOTW-A"]
    fam_isol = next(f for f in families if f.id == assignment["ISOL-A"])
    assert fam_isol.exclusions

    excl = fam_isol.exclusions[0]
    assert "DIFFERENT MECHANISM" in excl.basis
    assert any(c["dimension"] == "barrier" and c["match"] == "differs" for c in excl.dimension_comparisons)
