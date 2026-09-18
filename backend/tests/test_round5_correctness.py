"""5th-pass correctness suite.

Covers the four audited issues plus the mandatory negation cases:

1. Activity must NOT be inferred from weak context and canonical != evidence.
2. Strict provenance {value, basis, evidence_span}: Actual consequence is
   populated ONLY from explicit narrative statements; unstated -> unknown.
3. Family IDs must be deterministic / stable / unique.
4. Structural grouping must NEVER mix different barrier states.

Also: negated-outcome exposure guard, verified-family attention and the
data-driven WHY GROUPED evidence.
"""

from __future__ import annotations

import re

from app.config import get_settings
from app.services.normalization.ontology import get_ontology, normalize_text
from app.services.negation.engine import NegationEngine
from app.services.pipeline import AnalysisPipeline
from app.services.precursor.engine import PrecursorEngine


def _pipeline():
    return AnalysisPipeline(get_ontology(), get_settings())


def _obs(report_id: str, narrative: str):
    pipeline = _pipeline()
    o = pipeline.to_observation(report_id, narrative)
    o.id = report_id
    return o


# --------------------------------------------------------------------------
# Mandatory negation cases (SIH 2026 9-case list)
# --------------------------------------------------------------------------

def test_mandatory_case_1_verified():
    assert NegationEngine(get_ontology()).classify_sentence(
        "Isolation was verified.").state == "verified"


def test_mandatory_case_2_not_verified():
    assert NegationEngine(get_ontology()).classify_sentence(
        "Isolation was NOT verified.").state == "not_verified"


def test_mandatory_case_3_was_not_skipped_is_verified():
    """'Was not skipped' means the verification WAS performed -> verified.
    It must NEVER resolve to not_verified via the bare 'skipped' cue."""
    eng = NegationEngine(get_ontology())
    assert eng.classify_sentence(
        "Isolation was not skipped.").state == "verified"
    assert eng.classify_barrier(
        "energy_isolation", "Isolation was not skipped.").state == "verified"
    # The bare form stays a not_verified cue.
    assert eng.classify_sentence(
        "Isolation verification was skipped.").state == "not_verified"


def test_mandatory_cases_4_to_7():
    eng = NegationEngine(get_ontology())
    assert eng.classify_sentence(
        "Zero energy was confirmed.").state == "verified"
    assert eng.classify_sentence(
        "Zero energy was NOT confirmed.").state == "not_verified"
    assert eng.classify_sentence(
        "The isolation valve failed.").state == "failed"
    assert eng.classify_sentence(
        "The valve did not fail and held pressure.").state == "verified"


def test_mandatory_case_8_no_gas_released_exposure_stays_unknown():
    """'No gas was released' describes a NON-event and must never become an
    uncontrolled-gas-release exposure."""
    event = _pipeline().analyze(
        "MAND-8",
        "During pipeline maintenance, isolation was not verified and "
        "no gas was released.",
        provider="rules",
    ).event
    assert event.energy == "pressurized_gas"
    assert event.barrier == "energy_isolation"
    assert event.barrier_state == "not_verified"
    assert event.exposure == "unknown"
    assert not event.field_evidence.get("exposure", "")


def test_mandatory_case_9_not_carried_out_no_invented_exposure():
    event = _pipeline().analyze(
        "MAND-9", "Zero energy verification was not carried out.",
        provider="rules",
    ).event
    assert event.barrier_state == "not_verified"
    assert event.exposure == "unknown"


# --------------------------------------------------------------------------
# Issue 1 + 2: activity & actual-consequence provenance
# --------------------------------------------------------------------------

def test_activity_not_inferred_from_weak_context():
    """Bare 'maintenance' has no generic mapping -> Activity stays UNKNOWN;
    only an explicit 'pipeline maintenance' phrase produces the code with a
    verbatim evidence span."""
    generic = _pipeline().analyze(
        "PRV-1",
        "During maintenance, the crew reviewed the area and recorded a "
        "safety observation.",
        provider="rules",
    ).event
    assert generic.activity == "unknown"
    assert generic.field_basis["activity"] == "unknown"
    assert not generic.field_evidence.get("activity", "")

    explicit = _pipeline().analyze(
        "PRV-2",
        "During pipeline maintenance, isolation was not verified before the "
        "job began and gas was released from a flange.",
        provider="rules",
    ).event
    assert explicit.activity == "pipeline_maintenance"
    assert explicit.field_basis["activity"] == "explicit"
    span = explicit.field_evidence.get("activity", "")
    assert span and span in explicit.narrative
    assert span != explicit.activity  # canonical != evidence


def test_actual_consequence_unstated_is_unknown():
    event = _pipeline().analyze(
        "PRV-3",
        "During hot work in a storage tank, flammable vapour was present and "
        "gas testing had not been completed.",
        provider="rules",
    ).event
    assert event.actual_consequence == "unknown"
    assert event.field_basis["actual_consequence"] == "unknown"
    assert not event.field_evidence.get("actual_consequence", "")


def test_actual_consequence_no_injury_is_explicit_none_identified():
    event = _pipeline().analyze(
        "PRV-4",
        "During flange maintenance, isolation was not verified and gas was "
        "released. No injury was reported.",
        provider="rules",
    ).event
    assert event.actual_consequence == "none_identified"
    assert event.field_basis["actual_consequence"] == "explicit"
    span = event.field_evidence.get("actual_consequence", "")
    assert span and span in event.narrative


def test_actual_consequence_explicit_severe_surfaces_with_span():
    event = _pipeline().analyze(
        "PRV-5",
        "During flange maintenance work, zero energy was not confirmed before "
        "the job began and gas was heard leaking; this could have been fatal.",
        provider="rules",
    ).event
    assert event.actual_consequence == "serious_injury_or_fatality"
    assert event.potential_consequence == "serious_injury_or_fatality"
    assert event.potential_consequence_basis == "explicit"
    span = event.field_evidence.get("potential_consequence", "")
    assert span and span in event.narrative


# --------------------------------------------------------------------------
# Negated-outcome exposure guard
# --------------------------------------------------------------------------

def test_negates_outcome_shared_api():
    eng = NegationEngine(get_ontology())
    assert eng.negates_outcome(normalize_text("No gas was released."))
    assert eng.negates_outcome(normalize_text("Nothing leaked during the operation."))
    assert eng.negates_outcome(normalize_text("There was no release of gas."))
    assert eng.negates_outcome(normalize_text("No leak was reported."))
    # Positive statements / unrelated negations must NOT be treated as
    # non-events.
    assert not eng.negates_outcome(normalize_text("Gas was released from the flange."))
    assert not eng.negates_outcome(normalize_text("Gas was heard leaking."))
    assert not eng.negates_outcome(normalize_text("No further tests were done."))
    assert not eng.negates_outcome(normalize_text("The crew did not complete the checks."))


def test_exposure_guard_preserves_genuine_mixed_narratives():
    """A real release plus a negated clause keeps the genuine exposure; the
    guard only drops a release that is actually negated and nothing else."""
    event = _pipeline().analyze(
        "EXPO-1",
        "During pipeline maintenance, gas was heard leaking from a flange; "
        "no gas was released.",
        provider="rules",
    ).event
    assert event.exposure == "uncontrolled_gas_release"

    pure = _pipeline().analyze(
        "EXPO-2",
        "During pipeline maintenance, the isolation was verified before the "
        "job began and no gas was released.",
        provider="rules",
    ).event
    assert pure.exposure == "unknown"


# --------------------------------------------------------------------------
# Issue 3: family-id determinism / stability / uniqueness
# --------------------------------------------------------------------------

SCENARIO_A = (
    "During pipeline maintenance, isolation was not verified before the job "
    "began and gas was released from a flange."
)
SCENARIO_B = (
    "During compressor maintenance, the isolation was not verified before the "
    "casing was opened and gas was released."
)
SCENARIO_C = (
    "During pump maintenance on the gas line, the pump was isolated and "
    "locked out, zero pressure was confirmed before the casing was opened and "
    "gas was released."
)


def test_family_ids_deterministic_stable_and_unique():
    obs_a, obs_b, obs_c = (
        _obs("A", SCENARIO_A), _obs("B", SCENARIO_B), _obs("C", SCENARIO_C),
    )
    assert obs_a.event.exposure == "uncontrolled_gas_release"
    assert obs_b.event.exposure == "uncontrolled_gas_release"
    assert obs_c.event.barrier_state == "verified"
    assert obs_c.event.exposure == "uncontrolled_gas_release"

    engine = PrecursorEngine(get_ontology(), get_settings())

    fams1, asg1 = engine.run([obs_a, obs_b])
    assert set(asg1.values()) == {f.id for f in fams1}
    id_a = asg1["A"]
    assert id_a == asg1["B"]
    assert re.fullmatch(r"PFAM-[0-9A-F]{5}", id_a), id_a
    assert re.fullmatch(r"PFAM-[0-9A-F]{5}", asg1["A"])

    # Deterministic: rebuilding the same input yields identical ids.
    _fams2, asg2 = engine.run([obs_a, obs_b])
    assert asg2 == asg1

    # Verification & different mechanism get their own stable ids.
    fams3, asg3 = engine.run([obs_a, obs_b, obs_c])
    assert asg3["A"] == id_a
    assert asg3["B"] == id_a
    assert asg3["C"] != id_a
    assert re.fullmatch(r"PFAM-[0-9A-F]{5}", asg3["C"])
    assert len({f.id for f in fams3}) == 2
    for f in fams3:
        assert not (asg3["A"] == f.id and asg3["C"] == f.id)


def test_verified_and_not_verified_families_never_share_id():
    obs_a, obs_c = _obs("A", SCENARIO_A), _obs("C", SCENARIO_C)
    families, asg = PrecursorEngine(get_ontology(), get_settings()).run(
        [obs_a, obs_c]
    )
    assert asg["A"] != asg["C"]
    for fam in families:
        assert not (obs_a.id in fam.observation_ids
                    and obs_c.id in fam.observation_ids)


# --------------------------------------------------------------------------
# Issue 4: verified-family attention & controlled family type
# --------------------------------------------------------------------------

def test_verified_family_attention_not_elevated_by_failures():
    engine = PrecursorEngine(get_ontology(), get_settings())

    obs_p = [_obs(f"P{i}", SCENARIO_A) for i in range(2)]
    obs_v = [_obs(f"V{i}", SCENARIO_C) for i in range(2)]

    fams_p, _ = engine.run(obs_p)
    fams_v, _ = engine.run(obs_v)
    fam_p = fams_p[0]
    fam_v = fams_v[0]

    assert fam_v.family_type == "controlled"
    assert fam_p.family_type == "precursor"

    bf_v = next(f for f in fam_v.attention_factors if f["factor"] == "barrier_failure")
    assert bf_v["value"] == 0.0
    assert bf_v["contribution"] == 0.0
    assert not any("Failed-barrier" in b for b in fam_v.attention_basis)

    bf_p = next(f for f in fam_p.attention_factors if f["factor"] == "barrier_failure")
    assert bf_p["value"] == 1.0

    # Identical cardinality, energy and exposure; verified family is NOT
    # elevated by its (zero) failure frequency.
    assert fam_v.attention_signal < fam_p.attention_signal


def test_family_grouping_evidence_is_data_driven_and_excludes_potential():
    families, _ = PrecursorEngine(get_ontology(), get_settings()).run(
        [_obs("A", SCENARIO_A), _obs("B", SCENARIO_B)]
    )
    assert len(families) == 1
    fam = families[0]
    dims = [g.dimension for g in fam.grouping_evidence]
    assert dims
    assert "potential_consequence" not in dims
    assert set(dims) <= {
        "energy", "barrier", "barrier_state", "exposure",
        "task_phase", "activity",
    }
    for g in fam.grouping_evidence:
        assert g.status in ("same", "mixed", "distinct", "unknown")
    assert all(g.category in ("core_mechanism", "context") for g in fam.grouping_evidence)


# --------------------------------------------------------------------------
# Scenario E: fully-unknown observation stays unassigned
# --------------------------------------------------------------------------

def test_scenario_e_unknown_stays_needs_review_and_unassigned():
    narrative = (
        "During planning review, the team discussed future work at the "
        "compressor area; no work was in progress and no hazards were "
        "identified."
    )
    event = _pipeline().analyze("E-1", narrative, provider="rules").event
    assert event.needs_review is True
    assert event.sif.classification == "needs_review"

    obs = _obs("E-1", narrative)
    _families, asg = PrecursorEngine(get_ontology(), get_settings()).run([obs])
    assert asg["E-1"] == "UNASSIGNED / PENDING REVIEW"