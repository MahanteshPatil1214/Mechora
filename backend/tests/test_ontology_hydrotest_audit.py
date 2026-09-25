"""Ontology audit regressions: valve / pressure / isolation narratives.

Regresses the OIL safety-narrative audit for pressure, hydro-testing, valve,
bleed-line, isolation and stored-energy reports on the DETERMINISTIC rules
path (the LLM-path guard is covered in test_gemini_hydrotest_barrier_grounding).

The rules must keep the three evidence kinds distinct:

* HAZARD / ENERGY evidence ("pressure", "valve", "gas") grounds the energy
  field but is NEVER barrier evidence;
* EVENT / EXPOSURE evidence ("the valve ruptured", "a pressure release
  occurred", "crude oil spilled") grounds the exposure, never a barrier;
* CONTROL / BARRIER evidence ("isolation", "zero pressure confirmed",
  "was not verified") is the only thing that grounds ``energy_isolation``.

So a sudden pressure release with a ruptured valve, or a bare "the valve was
opened", or a blowout where only "gas" is mentioned, must NOT synthesize an
energy_isolation barrier from the hazard/event words alone.
"""

from __future__ import annotations

import json

import pytest

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

NHK162_NARRATIVE = (
    "During hydro-testing of the new pipeline at NHK-162, personnel were "
    "working near the valve when a sudden pressure release occurred and the "
    "valve ruptured."
)


def _analyze(report_id: str, narrative: str):
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    return pipeline.analyze(report_id, narrative, provider="rules").event


# ---------------------------------------------------------------------------
# Pressure / hydrotest / valve: hazard-or-event language is NOT a barrier
# ---------------------------------------------------------------------------


def test_nhk162_hydrotest_does_not_infer_energy_isolation():
    """The hydro-testing report names only the hazard (pressure) and the EVENT
    (pressure release, ruptured valve). No control is named, so no barrier is
    inferred and no barrier state is invented."""
    ev = _analyze("NHK162", NHK162_NARRATIVE)
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"
    assert ev.barrier != "energy_isolation"
    # The hazard itself is still legitimate ENERGY evidence.
    assert ev.energy in ("pressurized_gas", "pressurized_liquid")
    # The record is during the hydrotest, not before it.
    assert ev.task_phase == "testing"


def test_sudden_pressure_release_and_ruptured_valve_is_an_event():
    """Case 1: 'a sudden pressure release occurred and the valve ruptured' is
    event evidence. The \"ruptured\" failed-state cue must not bootstrap an
    energy_isolation barrier from hazard words."""
    ev = _analyze(
        "CASE-1",
        "During hydro-testing, a sudden pressure release occurred and the "
        "valve ruptured.",
    )
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"
    assert ev.barrier != "energy_isolation"


def test_valve_opened_alone_is_not_energy_isolation():
    """Case 5: 'the valve was opened' says nothing about an isolation control:
    valve is a HAZARD/component word, not a barrier."""
    ev = _analyze("CASE-5", "The valve was opened.")
    assert ev.barrier == "unknown"
    assert ev.energy == "unknown"
    assert ev.barrier != "energy_isolation"


def test_baghjan_blowout_gas_does_not_infer_energy_isolation():
    """'gas escaped and the well failed' is EVENT evidence: 'gas' is a hazard
    word. The barrier must stay unknown instead of being invented from gas."""
    ev = _analyze(
        "BAGHJAN",
        "The gas well at the Baghjan site experienced a massive blowout; gas "
        "escaped and the well failed during maintenance.",
    )
    assert ev.barrier == "unknown"
    assert ev.barrier_state == "unknown"
    assert ev.energy == "pressurized_gas"
    assert ev.exposure == "uncontrolled_gas_release"


# ---------------------------------------------------------------------------
# Control language STILL grounds energy_isolation (nothing over-suppressed)
# ---------------------------------------------------------------------------


def test_isolation_not_verified_before_opening_grounds_barrier():
    """Case 2: explicit isolation-control language keeps energy_isolation with
    its deterministic not_verified state."""
    ev = _analyze(
        "CASE-2", "Isolation was not verified before opening the line."
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"


def test_zero_pressure_confirmed_grounds_barrier_verified():
    """Case 3: zero-pressure verification is a positive control observation."""
    ev = _analyze(
        "CASE-3", "Zero pressure was confirmed before opening the line."
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "verified"


def test_zero_pressure_not_confirmed_grounds_barrier_not_verified():
    """Case 4: zero-pressure verification that did not happen stays a negated
    control observation."""
    ev = _analyze(
        "CASE-4", "Zero pressure was not confirmed before opening the line."
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"


def test_isolation_valve_not_secured_grounds_barrier_not_verified():
    """Case 6: 'isolation valve ... not secured' names the control; the control
    word (not the valve component) grounds the barrier."""
    ev = _analyze("CASE-6", "The isolation valve was not secured.")
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"
    assert ev.exposure == "unknown"


def test_pressure_released_and_confirmed_zero_is_control_evidence():
    """A released-and-confirmed-zero reading is a CONTROL observation: the
    hazard word 'pressure' bootstraps energy_isolation only because the
    verification state is determinate."""
    ev = _analyze(
        "CTRL-1",
        "During pipeline maintenance, the pressure was released and confirmed "
        "zero before the joints were opened.",
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "verified"


def test_pressure_not_released_before_opening_is_not_verified():
    ev = _analyze(
        "CTRL-2",
        "During pipeline maintenance, the pressure was not released before the "
        "joints were opened.",
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"


def test_ruptured_valve_with_isolation_control_stays_energy_isolation():
    """test_hardening PTW-6: when the isolation control IS named, a ruptured
    valve is a genuine barrier failure and must keep energy_isolation+failed."""
    ev = _analyze(
        "PTW-6",
        "Pump repair: the isolation valve ruptured and failed to hold pressure "
        "during maintenance, gas escaped.",
    )
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "failed"


# ---------------------------------------------------------------------------
# Ontology coverage: liquid / rupture / spill / dislodgement / steam
# ---------------------------------------------------------------------------


def test_crude_pipeline_rupture_maps_to_liquid_energy_and_exposure():
    """Crude pipeline rupture: the substance (crude oil) grounds pressurized
    liquid; 'spilled' grounds the liquid exposure; no control is named."""
    ev = _analyze(
        "RUPT-CRUDE",
        "The pipeline ruptured and crude oil spilled onto the ground.",
    )
    assert ev.energy == "pressurized_liquid"
    assert ev.exposure == "uncontrolled_liquid_release"
    assert ev.barrier == "unknown"


def test_hydrotest_water_maps_to_pressurized_liquid():
    ev = _analyze(
        "HYDRO-WATER",
        "During the hydrotest, hydrotest water remained in the line and was "
        "released when the joint was opened.",
    )
    assert ev.energy == "pressurized_liquid"


def test_dislodged_flange_is_struck_by_exposure():
    ev = _analyze(
        "DISLODGE",
        "The flange came loose and the joint dislodged during maintenance.",
    )
    assert ev.exposure == "object_drop_struck_by"


def test_steam_release_not_confused_with_gas_release():
    """Steam beat the shared 'ruptured' event word via the longest-span
    tie-break: 'steam was released' outranks gas/liquid's bare 'ruptured'."""
    ev = _analyze(
        "STEAM-RUPT",
        "High-pressure steam was released from the ruptured gasket.",
    )
    assert ev.exposure == "uncontrolled_steam_release"


def test_task_phase_hydrotest_is_testing_not_pre_job():
    """'hydrotest' must not be read as the bare word 'test': the hydrotest is
    the phase the incident happened IN, not a pre-job verification signal."""
    ev = _analyze(
        "TP-HYDRO",
        "During hydro-testing of the new pipeline, the flange was loosened.",
    )
    assert ev.task_phase == "testing"


# ---------------------------------------------------------------------------
# Hydrostatic-testing observation, end to end
# ---------------------------------------------------------------------------

HYDROTEST_OBS_NARRATIVE = (
    "During hydrostatic testing of a newly installed pipeline at the well site, "
    "the test line was pressurized with water. While personnel were working near "
    "the connection, the bleed valve and connected line suddenly came loose, "
    "resulting in an uncontrolled release of pressurized water. No isolation or "
    "zero-pressure verification was mentioned before the connection was opened. "
    "No injury was reported."
)


def test_hydrotest_observation_end_to_end():
    """The full observation resolves to a testing-phase pipeline task with a
    pressurized-liquid hazard, an unverified energy-isolation control, a liquid
    release exposure, and a high SIF potential — in one coherent extraction."""
    ev = _analyze("HYDROTEST-OBS", HYDROTEST_OBS_NARRATIVE)
    assert ev.activity == "pipeline_maintenance"
    assert ev.task_phase == "testing"
    assert ev.energy == "pressurized_liquid"
    assert ev.barrier == "energy_isolation"
    assert ev.barrier_state == "not_verified"
    assert ev.exposure == "uncontrolled_liquid_release"
    assert ev.potential_consequence == "serious_injury_or_fatality"
    assert ev.location == "well_site"
    assert "energy_isolation" in ev.life_saving_rules
    assert ev.sif.classification == "high"
    assert ev.needs_review is False
    assert not ev.missing_fields


def test_hydrotest_observation_evidence_is_grounded():
    """The choice of values is auditable through grounded evidence spans: the
    phase, hazard, release and control observations each map to exact text."""
    ev = _analyze("HYDROTEST-OBS2", HYDROTEST_OBS_NARRATIVE)
    fe = ev.field_evidence
    assert "hydrostatic testing" in fe.get("task_phase", "").lower()
    assert "pressurized" in fe.get("energy", "").lower()
    assert "uncontrolled release of pressurized water" in fe.get(
        "exposure", ""
    ).lower()
    assert "zero-pressure verification" in fe.get("barrier_state", "").lower()
    assert fe.get("activity", "").lower() in ("newly installed pipeline",)


def test_specific_testing_phrases_are_authoritative_testing_phase():
    """Compound ontology testing phrases name the phase the incident happened
    IN; they may not be downgraded by the activity-implied maintenance or by
    the bare-word pre-job verification heuristic."""
    for i, phrase in enumerate(
        ("During hydrostatic testing, the pipeline was pressurized with water.",
         "During hydrotest, the pipeline was pressurized with water.",
         "During pressure testing, the pipeline was pressurized with water.",
         "During the pressure test, the line was pressurized with water.")
    ):
        ev = _analyze(f"TP-SPEC-{i}", phrase)
        assert ev.task_phase == "testing", phrase
        assert ev.activity == "pipeline_maintenance", phrase


def test_before_starting_maintenance_stays_pre_job_not_testing():
    """'Before starting maintenance' is a preparation step — pre_job — even
    though maintenance is a known activity."""
    ev = _analyze(
        "TP-D", "Before starting maintenance, the crew completed the pre-job "
                "verification."
    )
    assert ev.task_phase == "pre_job"
    assert ev.task_phase != "testing"


@pytest.mark.parametrize(
    "narrative",
    [
        "Gas testing was not carried out before work.",
        "Gas testing was carried out before work.",
    ],
)
def test_gas_testing_before_work_stays_pre_job(narrative):
    """Bare 'testing' near a 'before work' cue is a PRE-JOB gas test, not a
    testing task phase (freezes EVAL-919/EVAL-920 behaviour)."""
    ev = _analyze("TP-GAS", narrative)
    assert ev.task_phase == "pre_job"


def test_valve_came_loose_with_release_is_liquid_exposure():
    """A came-loose event that ends in an uncontrolled liquid release is a
    liquid RELEASE event, not a struck-by: the release outranks the component
    movement exposure."""
    ev = _analyze(
        "EX-CAMELOOSE",
        "A valve came loose and an uncontrolled release of pressurized water "
        "occurred.",
    )
    assert ev.energy == "pressurized_liquid"
    assert ev.exposure == "uncontrolled_liquid_release"


@pytest.mark.parametrize(
    ("narrative", "report_id"),
    [
        ("A loose component fell from the structure and struck a worker.",
         "STRIKE-FELL"),
        ("A component became dislodged and struck a worker.", "STRIKE-DISLODGE"),
        ("An object became detached and fell onto a worker.", "STRIKE-DETACH"),
    ],
)
def test_object_striking_a_worker_is_object_drop_struck_by(narrative, report_id):
    """Object-on-person contact ('struck a worker', 'fell onto a worker') is a
    struck-by event; the bare object 'fell' must not demote it to a passive
    fall-from-height."""
    ev = _analyze(report_id, narrative)
    assert ev.exposure == "object_drop_struck_by"
    assert ev.exposure != "fall_from_height"


def test_worker_own_fall_stays_fall_from_height():
    """A worker's own fall (slip from a platform) remains fall_from_height; the
    struck-by override only fires on explicit object-on-person contact."""
    ev = _analyze(
        "FALL-WORKER",
        "The worker slipped from the platform and had a fall from height.",
    )
    assert ev.exposure == "fall_from_height"


def test_hydrotest_came_loose_without_release_is_struck_by():
    """A bare came-loose event during a hydrotest (no release, no isolation
    control) stays a struck-by exposure, not an invented liquid release."""
    ev = _analyze(
        "HYDRO-LOOSE",
        "During hydrostatic testing, the bleed valve came loose. No injury was "
        "reported.",
    )
    assert ev.task_phase == "testing"
    assert ev.exposure == "object_drop_struck_by"


# ---------------------------------------------------------------------------
# Ontology consistency for the new audit tables
# ---------------------------------------------------------------------------


def test_hazard_context_terms_are_subset_of_context_terms():
    """Every barrier_hazard_context_term must be reachable from the barrier's
    barrier_context_terms, otherwise the gate could never apply to it."""
    ontology = get_ontology()
    cues = ontology.negation_cues()
    context = cues.get("barrier_context_terms", {})
    hazard = cues.get("barrier_hazard_context_terms", {})
    assert hazard, "barrier_hazard_context_terms must be populated"
    valid = set(ontology.codes("barrier"))
    for code, terms in hazard.items():
        if code.startswith("_"):
            continue
        assert code in valid, code
        assert terms, code
        assert code in context, code
        # At least the hazard words shared with the barrier's context terms
        # must render the gate reachable ("pressure"/"valve"/"gas" for
        # energy_isolation); the rest are documentation for future additions.
        assert set(terms) & set(context[code]), (code, context.get(code))


def test_lsr_energy_to_rule_covers_every_energy():
    """The recognition gap is closed: pressurized_liquid is now mapped the same
    way as pressurized_gas, and no energy lacks an LSR mapping."""
    ontology = get_ontology()
    table = ontology.lsr_table()
    e2r = table.get("energy_to_rule", {})
    energies = {c.code for c in ontology.concepts("energy")}
    assert "pressurized_liquid" in e2r
    assert e2r["pressurized_liquid"] == ["energy_isolation"]
    assert energies <= set(e2r), energies - set(e2r)


def test_energy_synonyms_added_are_present():
    ontology = get_ontology()
    gas_syns = ontology.concept("energy", "pressurized_gas").synonyms
    liq_syns = ontology.concept("energy", "pressurized_liquid").synonyms
    assert "stored pressure" in gas_syns
    assert "hydrotest water" in liq_syns
    assert "water under pressure" in liq_syns


def test_eval_set_has_no_audit_vocabulary_collisions():
    """The new exposure/energy synonyms must not collide with any frozen eval
    narrative (proving the additions are eval-neutral by construction)."""
    doc = json.loads(get_settings().eval_set_path.read_text(encoding="utf-8"))
    needles = ("ruptur", "burst", "dislodg", "came loose", "came off",
               "broke off", "hydrotest", "condensate", "spilled",
               "well plinth", "stored pressure", "pressure buildup",
               "hydrostatic", "pressure testing", "pressurized water",
               "pressurized with water", "uncontrolled release",
               "release of water", "newly installed", "test line",
               "struck a worker", "fell onto", "during testing",
               "test run", "trial run")
    for rec in doc["records"]:
        low = rec["narrative"].lower()
        for needle in needles:
            assert needle not in low, (rec["report_id"], needle)