"""Architecture-hardening suite (round 6).

Covers the hardening contract:

1. Demo scenarios 1-8 (different stories -> same failed barrier -> recurring
   precursor; verified / failed / different-barrier / vague all stay separate).
2. Structural hard boundaries: different barrier, barrier state, energy AND
   exposure never merge; single-linkage cannot bridge them.
3. Negation applicability guard: "isolation was NOT required" is not a
   barrier failure (never not_verified/failed; resolves to unknown/needs-review).
4. Evidence grounding: field_basis EXPLICIT vs INFERRED vs UNKNOWN, with all
   explicit spans verbatim in the narrative.
5. Consequence non-fabrication: an unsupported potential consequence is never
   invented as explicit.
6. Extraction fallback provenance: requested_provider / fallback_used /
   fallback_reason are captured on the analysis result and on the observation,
   and survive an LLM failure at runtime.
7. HSE human-in-the-loop: validation records reviewer / reason / timestamp.
8. Canonical event = single source of truth: evidence grounding, consequence,
   SIF, LSR, signature and grouping are provider-independent — an LLM may only
   propose values (language), the pipeline re-derives every safety decision
   deterministically.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.database import repos
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.services.precursor.engine import PrecursorEngine


def _pipeline():
    return AnalysisPipeline(get_ontology(), get_settings())


def _obs(report_id: str, narrative: str, provider: str = "rules"):
    pipeline = _pipeline()
    o = pipeline.to_observation(report_id, narrative, provider=provider)
    o.id = report_id
    return o


def _families(obs_list):
    engine = PrecursorEngine(get_ontology(), get_settings())
    return engine.run(obs_list)


# --------------------------------------------------------------------------
# Demo scenarios 1-8
# --------------------------------------------------------------------------

NOT_VERIFIED_ISOLATION = [
    ("PTW-1", "Pipeline flange maintenance: zero energy was not verified "
              "before the joint was opened; gas released."),
    ("PTW-2", "Pump overhaul: nobody confirmed zero pressure before the "
              "casing was opened; gas escaped."),
    ("PTW-3", "Valve maintenance: zero energy was never checked before "
              "unbolting; gas leaked out."),
    ("PTW-4", "Compressor service: isolation verification was skipped "
              "before work; gas was released."),
]

UNASSIGNED = "UNASSIGNED / PENDING REVIEW"

VERIFIED = (
    "PTW-5", "Pipeline flange maintenance: zero energy was verified and "
             "isolation confirmed before work started."
)
FAILED = (
    "PTW-6", "Pump repair: the isolation valve ruptured and failed to hold "
             "pressure during maintenance; gas escaped."
)
DIFFERENT_BARRIER = (
    "PTW-7", "Pipeline repair: gas testing was not completed before grinding "
             "began; spark ignited vapour."
)
VAGUE = (
    "PTW-8", "Maintenance was performed on equipment."
)


def test_scenarios_1_4_same_failed_barrier_recurring_cluster():
    """Four different stories (pipeline/pump/valve/compressor) sharing the
    same failed barrier + energy + exposure must converge into ONE recurring
    precursor family while activity stays a context dimension."""
    obs = [_obs(rid, text) for rid, text in NOT_VERIFIED_ISOLATION]
    families, assignment = _families(obs)
    fam_ids = {assignment[rid] for rid, _ in NOT_VERIFIED_ISOLATION}
    assert len(fam_ids) == 1, f"expected 1 recurring family, got {fam_ids}"
    fam = next(f for f in families if f.id == fam_ids.pop())
    assert fam.common_barrier == "energy_isolation"
    assert fam.common_barrier_state == "not_verified"
    assert fam.common_energy == "pressurized_gas"
    assert fam.common_exposure == "uncontrolled_gas_release"
    assert fam.recurring is True
    assert len(fam.observation_ids) == 4
    # Activity is context, never a hard-grouping boundary.
    act = {o.event.activity for o in obs}
    assert len(act) >= 3


def test_scenario_5_verified_stays_separate():
    """The same barrier under VERIFIED state must NEVER join the failure
    story even with matching activity/location wording."""
    obs = [_obs(rid, text) for rid, text in NOT_VERIFIED_ISOLATION]
    obs.append(_obs(*VERIFIED))
    families, assignment = _families(obs)
    not_ver = assignment["PTW-1"]
    ver = assignment[VERIFIED[0]]
    assert ver != not_ver
    assert ver == UNASSIGNED, "verified obs is held, not force-familied"
    assert not any(VERIFIED[0] in f.observation_ids for f in families)
    fam_not_ver = next(f for f in families if f.id == not_ver)
    assert fam_not_ver.common_barrier_state == "not_verified"


def test_scenario_6_failed_stays_separate_from_not_verified():
    """Mechanical barrier FAILURE must never merge with procedural
    not_verified, though both are 'not good' stories on energy isolation."""
    obs = [_obs(rid, text) for rid, text in NOT_VERIFIED_ISOLATION]
    obs.append(_obs(*FAILED))
    families, assignment = _families(obs)
    assert assignment[FAILED[0]] != assignment["PTW-1"]


def test_scenario_7_different_barrier_stays_separate():
    """Hot-work controls (gas testing) is a different mechanism than energy
    isolation; both stories must stay separate."""
    obs = [_obs(rid, text) for rid, text in NOT_VERIFIED_ISOLATION]
    obs.append(_obs(*DIFFERENT_BARRIER))
    families, assignment = _families(obs)
    hotw = assignment[DIFFERENT_BARRIER[0]]
    assert hotw != assignment["PTW-1"]
    fam_hotw = next(f for f in families if f.id == hotw)
    assert fam_hotw.common_barrier == "hot_work_controls"


def test_scenario_8_vague_narrative_held_for_review():
    """An observation with no hazard/barrier/exposure evidence must be flagged
    NEEDS REVIEW and never forced into a precursor family."""
    obs = _obs(*VAGUE)
    assert obs.event.needs_review is True
    for f in ("barrier", "barrier_state", "energy", "exposure"):
        assert f in obs.event.missing_fields
    assert obs.event.sif.classification == "needs_review"
    assert obs.event.potential_consequence == "unknown"
    families, assignment = _families([obs])
    assert assignment[VAGUE[0]] == UNASSIGNED, "vague obs must stay unassigned"


# --------------------------------------------------------------------------
# Structural hard boundaries (task: don't over-merge)
# --------------------------------------------------------------------------

def test_exposure_is_a_hard_grouping_boundary():
    """Same failed barrier, same state, same energy, DIFFERENT exposure is a
    different precursor (gas release vs ignition flash) and must not merge."""
    gas = _obs("FLG-GAS",
        "Flange maintenance: zero energy was not verified before the joint "
        "was opened; gas released.")
    fire = _obs("FLG-FIRE",
        "Flange maintenance: zero energy was not verified before the joint "
        "was opened; the released gas ignited in a flash.")
    assert gas.event.barrier == fire.event.barrier == "energy_isolation"
    assert gas.event.barrier_state == fire.event.barrier_state == "not_verified"
    assert gas.event.energy == fire.event.energy == "pressurized_gas"
    assert gas.event.exposure == "uncontrolled_gas_release"
    assert fire.event.exposure == "fire_or_explosion"
    families, assignment = _families([gas, fire])
    assert assignment[gas.id] != assignment[fire.id]
    for fam in families:
        assert not (gas.id in fam.observation_ids
                    and fire.id in fam.observation_ids)


def test_failed_verified_and_not_verified_stay_separate_as_triplet():
    obs = [
        _obs("TRIP-A", NOT_VERIFIED_ISOLATION[0][1]),
        _obs("TRIP-B", VERIFIED[1]),
        _obs("TRIP-C", FAILED[1]),
    ]
    for o, rid in zip(obs, ("TRIP-A", "TRIP-B", "TRIP-C")):
        o.id = rid
    families, assignment = _families(obs)
    assert len({assignment["TRIP-A"], assignment["TRIP-B"],
                assignment["TRIP-C"]}) == 3


# --------------------------------------------------------------------------
# Negation applicability guard
# --------------------------------------------------------------------------

def test_not_required_is_not_a_barrier_failure():
    """'Isolation was NOT required' describes a non-applicable barrier, NOT a
    skipped/failed one. It must never resolve to not_verified or failed and
    must never be counted as a recurring barrier failure."""
    from app.services.negation.engine import NegationEngine

    eng = NegationEngine(get_ontology())
    for sentence in (
        "Isolation was not required for this task.",
        "Zero energy isolation was not needed on this equipment.",
        "The isolation was not necessary here.",
    ):
        res = eng.classify_sentence(sentence)
        assert res.state == "unknown", (sentence, res.state)
        assert res.state not in ("not_verified", "failed")

    obs = _obs("NREQ-1", "Isolation was not required for this task.")
    assert obs.event.barrier_state == "unknown"
    assert obs.event.needs_review is True


def test_not_required_never_drives_failure_family():
    """A 'not required' story must not inflate the not_verified precursor
    family count."""
    obs = [
        _obs("FLG-1", "Flange maintenance: zero energy was not verified "
                      "before the joint was opened; gas released."),
        _obs("NREQ-1", "Isolation was not required for this task."),
    ]
    families, assignment = _families(obs)
    assert assignment["NREQ-1"] == UNASSIGNED, (
        "non-applicable barrier must not join a failure family"
    )
    fam_flg = next(f for f in families if f.id == assignment["FLG-1"])
    assert "NREQ-1" not in fam_flg.observation_ids


def test_negated_outcome_override_keeps_real_failure():
    """A negated outcome ('no gas was released') must NOT blind an explicit
    control failure in the same sentence."""
    from app.services.negation.engine import NegationEngine

    eng = NegationEngine(get_ontology())
    res = eng.classify_barrier(
        "energy_isolation",
        "Isolation was not verified and no gas was released.",
    )
    assert res.state == "not_verified"


# --------------------------------------------------------------------------
# Evidence grounding & consequence non-fabrication
# --------------------------------------------------------------------------

def test_field_basis_is_explicit_only_with_verbatim_spans():
    ev = _pipeline().analyze(
        "EVID-1",
        "During flange maintenance work, zero energy was not confirmed before "
        "the job began and gas was heard leaking from the flange.",
        provider="rules",
    ).event
    # Values that have a supporting span are EXPLICIT.
    assert ev.field_basis["activity"] == "explicit"
    assert ev.field_basis["barrier"] == "explicit"
    assert ev.field_basis["barrier_state"] == "explicit"
    assert ev.field_basis["energy"] == "explicit"
    assert ev.field_basis["exposure"] == "explicit"
    # Rule-inferred potential consequence is never presented as a quote.
    assert ev.field_basis["potential_consequence"] != "explicit"
    for key, span in ev.field_evidence.items():
        assert span in ev.narrative, f"{key} evidence not verbatim: {span!r}"


def test_unknown_basis_for_unstated_fields():
    ev = _pipeline().analyze(
        "EVID-2", "Zero energy verification was not carried out.",
        provider="rules",
    ).event
    assert ev.field_basis["activity"] == "unknown"
    assert ev.field_basis["location"] == "unknown"
    assert ev.field_basis["energy"] == "unknown"
    assert ev.field_basis["exposure"] == "unknown"


def test_unsupported_potential_consequence_is_not_invented():
    """A bare release statement ('A hydrocarbon release occurred.') never
    fabricates an explicit consequence. If one is inferred it must be labeled
    model_inference; explicit requires a verbatim severe-outcome statement."""
    ev = _pipeline().analyze(
        "PC-1", "A hydrocarbon release occurred.", provider="rules"
    ).event
    assert ev.field_basis["potential_consequence"] != "explicit"
    assert not ev.field_evidence.get("potential_consequence", "")

    ev_expl = _pipeline().analyze(
        "PC-2", "A hydrocarbon release occurred; this could have been fatal.",
        provider="rules",
    ).event
    assert ev_expl.potential_consequence_basis == "explicit"
    span = ev_expl.field_evidence.get("potential_consequence", "")
    assert span and span in ev_expl.narrative


# --------------------------------------------------------------------------
# Extraction fallback provenance
# --------------------------------------------------------------------------

def test_fallback_provenance_on_llm_failure():
    pipeline = _pipeline()
    def boom(_rid, _narrative):
        raise RuntimeError("simulated Gemini outage")
    pipeline.llm_extractor.extract = boom

    result = pipeline.analyze("FALL-1", NOT_VERIFIED_ISOLATION[0][1],
                              provider="llm")
    assert result.provider == "rules", "must degrade gracefully to rules"
    assert result.requested_provider == "llm"
    assert result.fallback_used is True
    assert result.fallback_reason
    assert result.warnings, "degradation must be surfaced to the UI"


def test_rule_path_has_no_fallback_story():
    pipeline = _pipeline()
    result = pipeline.analyze("RULES-1", NOT_VERIFIED_ISOLATION[0][1],
                              provider="rules")
    assert result.provider == "rules"
    assert result.requested_provider == "rules"
    assert result.fallback_used is False
    assert result.fallback_reason == ""


def test_observation_carries_provenance_fields():
    o = _obs("PROV-1", NOT_VERIFIED_ISOLATION[0][1], provider="rules")
    assert o.provider == "rules"
    assert o.requested_provider == "rules"
    assert o.fallback_used is False


# --------------------------------------------------------------------------
# HSE human-in-the-loop
# --------------------------------------------------------------------------

def test_validation_records_reviewer_reason_timestamp():
    o = _obs("HSE-1", NOT_VERIFIED_ISOLATION[0][1])
    saved = repos.create_observation(o, recompute=False)
    assert saved.validation == "pending"

    updated = repos.update_validation(
        saved.id, "validated",
        reviewer="R. HSE Lead", reason="matches field report",
    )
    assert updated.validation == "validated"
    assert updated.validation_reviewer == "R. HSE Lead"
    assert updated.validation_reason == "matches field report"
    assert updated.validated_at

    round_trip = repos.get_observation(saved.id)
    assert round_trip.validation == "validated"
    assert round_trip.validation_reviewer == "R. HSE Lead"
    assert round_trip.validation_reason == "matches field report"
    assert round_trip.validated_at == updated.validated_at


# --------------------------------------------------------------------------
# Canonical event = single source of truth (provider-independent safety logic)
# --------------------------------------------------------------------------

def _llm_result(report_id: str, narrative: str):
    """Analyze through the LANGUAGE-only path with the LLM stubbed to return
    exactly the structured values the rules engine would produce. Any drift in
    barrier state, consequence, SIF, LSR or grouping can then only come from
    the pipeline's deterministic layer, never from the model."""
    pipeline = _pipeline()
    out = pipeline.rule_extractor.extract(report_id, narrative)
    pipeline.llm_extractor.extract = (
        lambda _rid, _narr: (out.extraction, {"provider": "llm"})
    )
    return pipeline.analyze(report_id, narrative, provider="llm")


def test_llm_path_evidence_grounding_matches_rules_path():
    """Evidence attribution must be provider-independent: when an LLM proposes
    the same canonical values as rules, field_basis and field_evidence are
    identical, and every claimed span is verbatim."""
    narrative = ("During flange maintenance work, zero energy was not "
                 "confirmed before the job began and gas was heard leaking "
                 "from the flange.")
    ev_rules = _pipeline().analyze(
        "EVID-L1", narrative, provider="rules").event
    ev_llm = _llm_result("EVID-L2", narrative).event
    for field in ("activity", "task_phase", "energy", "barrier",
                  "barrier_state", "exposure", "location",
                  "actual_consequence", "potential_consequence"):
        assert ev_llm.field_basis[field] == ev_rules.field_basis[field], field
    for span in ev_llm.field_evidence.values():
        assert span in narrative, f"LLM-path evidence not verbatim: {span!r}"
    assert ev_llm.field_basis["exposure"] == "explicit"
    assert ev_llm.field_evidence.get("barrier_state") == \
        ev_rules.field_evidence.get("barrier_state")


def test_llm_path_never_attaches_negated_exposure_span():
    """An LLM-proposed exposure is NOT 'explicit' when the narrative negates
    the release ('none was released'): the value may stay (model-suggested,
    inferred) but the negated phrase must never be attached as its evidence."""
    from app.models.safety_event import LLMExtraction

    pipeline = _pipeline()
    raw = LLMExtraction(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        barrier="energy_isolation",
        barrier_state="not_verified",
        exposure="uncontrolled_gas_release",
        evidence=["zero energy was not verified", "none was released"],
    )
    pipeline.llm_extractor.extract = (
        lambda _rid, _narr: (raw, {"provider": "llm"})
    )
    ev = pipeline.analyze(
        "EVID-NEG",
        "Flange maintenance: zero energy was not verified; gas was contained, "
        "none was released.",
        provider="llm",
    ).event
    assert ev.exposure == "uncontrolled_gas_release"
    assert ev.field_basis["exposure"] != "explicit"
    assert not ev.field_evidence.get("exposure", "")


def test_canonical_event_drives_all_downstream_layers_identically():
    """SIF, LSR, signature and family assignment are computed ONLY from the
    canonical event, so the rules and (identically-valued) LLM paths produce
    the same safety results."""
    from app.models.safety_event import Observation

    obs_r = [_obs(rid, t) for rid, t in NOT_VERIFIED_ISOLATION]
    obs_l = []
    for rid, t in NOT_VERIFIED_ISOLATION:
        r = _llm_result(rid, t)
        o = Observation(report_id=rid, narrative=t, provider="llm",
                        requested_provider="llm", event=r.event)
        o.id = rid
        obs_l.append(o)
    fam_r, asg_r = _families(obs_r)
    fam_l, asg_l = _families(obs_l)
    for rid, _ in NOT_VERIFIED_ISOLATION:
        assert asg_r[rid] == asg_l[rid], rid
    assert {f.id for f in fam_r} == {f.id for f in fam_l}
    for o_r, o_l in zip(obs_r, obs_l):
        assert o_r.event.sif.classification == o_l.event.sif.classification
        assert o_r.event.lsr_mapping.rules == o_l.event.lsr_mapping.rules
        assert o_r.event.precursor_signature == o_l.event.precursor_signature


def test_resolved_provider_is_exposed():
    """The provenance vocabulary exposes requested_provider, resolved_provider,
    fallback_used and fallback_reason on the analysis result."""
    def boom(_rid, _narr):
        raise RuntimeError("simulated Gemini outage")

    pipeline = _pipeline()
    pipeline.llm_extractor.extract = boom
    res_llm = pipeline.analyze("RES-1", NOT_VERIFIED_ISOLATION[0][1],
                               provider="llm")
    assert res_llm.resolved_provider == "rules" == res_llm.provider
    assert res_llm.requested_provider == "llm"
    assert res_llm.fallback_used is True

    res_rules = pipeline.analyze("RES-2", NOT_VERIFIED_ISOLATION[0][1],
                                 provider="rules")
    assert res_rules.resolved_provider == "rules" == res_rules.provider
    assert res_rules.requested_provider == "rules"
    assert res_rules.fallback_used is False