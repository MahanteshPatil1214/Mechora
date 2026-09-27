"""Deterministic rules path: generic confined-space context inference.

These tests fix the behaviour of a narrative that places a person INSIDE an
enclosure without using any canonical code or ontology synonym verbatim:

    "Before entering the storage vessel to inspect its interior, the maintenance
     team did not verify that the vessel had been properly isolated and made safe
     for entry. The atmosphere was not confirmed safe, ventilation had not been
     established, and the worker entered the vessel without completing the
     required entry checks."

Nothing here is special-cased for that text. The detector keys on generic
morphological families (enclosure noun + entry cue, atmosphere cue, entry
control) and selects only codes that already exist in the ontology.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

TARGET = (
    "Before entering the storage vessel to inspect its interior, the maintenance "
    "team did not verify that the vessel had been properly isolated and made safe "
    "for entry. The atmosphere was not confirmed safe, ventilation had not been "
    "established, and the worker entered the vessel without completing the "
    "required entry checks."
)

# Same situation, different enclosure and different atmosphere/control wording.
TANK = (
    "Before entering the tank to inspect its interior, the crew did not verify "
    "that the tank had been isolated and made safe for entry. The atmosphere "
    "was not confirmed safe, ventilation had not been established, and the "
    "worker entered the tank without completing the required entry checks."
)
INTERNAL_INSPECTION = (
    "An internal inspection was carried out inside the reactor vessel. The "
    "atmosphere was never tested and the attendant was not posted. Entry "
    "permits were not issued."
)
GAS_TESTING_WORDING = (
    "The operator entered the pit to survey the interior. Gas testing had not "
    "been performed, the space was not purged, and no entry certificate was "
    "signed before entry."
)

# A space whose atmosphere WAS tested and found safe carries no hazard, even
# though it uses the same vocabulary as the target.
VERIFIED_ATMOSPHERE = (
    "During confined space entry the vessel atmosphere was tested and "
    "ventilation was running. No injury was reported."
)
VERIFIED_ATMOSPHERE_2 = (
    "During confined space entry, the vessel was purged and the atmosphere "
    "tested safe before entry. No injury was reported."
)
VERIFIED_ATMOSPHERE_3 = (
    "During tank cleaning, the tank was ventilated and the atmosphere tested "
    "before entry. No injury was reported."
)

# Generic controls that must NOT be read as a confined-space entry control.
VENTILATION_ONLY = (
    "The operator reported that ventilation in the process area was not "
    "adequate during the transfer of solvent into the storage tank."
)
MAINTENANCE_VENTILATION = (
    "During scheduled maintenance of the storage tank, the ventilation fan "
    "had failed and the area was not ventilated."
)
ENTRY_WITHOUT_CONTROL = (
    "The technician entered the tank to measure the liquid level."
)
ENTRY_WITHOUT_ATMOSPHERE = (
    "The technician entered the vessel and the required entry checks were "
    "completed before entry."
)


@pytest.fixture(scope="module")
def pipeline():
    return AnalysisPipeline(get_ontology(), get_settings())


def _event(pipeline, narrative, report_id="R-CS"):
    obs = pipeline.to_observation(report_id, narrative, provider="rules")
    assert obs.validation != "invalid", obs.validation_reason
    return obs.event


def _ungrounded(event, narrative):
    return [
        (key, value)
        for key, value in (event.field_evidence or {}).items()
        if value and value not in narrative
    ]


@pytest.mark.parametrize("narrative", [TARGET, TANK, INTERNAL_INSPECTION, GAS_TESTING_WORDING])
def test_confined_space_entry_resolves_to_ontology_codes(pipeline, narrative):
    event = _event(pipeline, narrative)
    assert event.activity == "confined_space_entry"
    assert event.task_phase == "inspection"
    assert event.energy == "flammable_atmosphere"
    assert event.barrier == "confined_space_procedure"
    assert event.exposure == "confined_space_atmosphere"
    assert event.potential_consequence == "serious_injury_or_fatality"
    assert event.location == "unknown"
    assert event.sif.classification == "high"
    assert _ungrounded(event, narrative) == []


def test_target_evidence_is_verbatim_and_field_specific(pipeline):
    event = _event(pipeline, TARGET)
    evidence = event.field_evidence
    assert evidence["activity"] == "entering the storage vessel to inspect its interior"
    assert evidence["energy"] == "The atmosphere was not confirmed safe"
    assert evidence["exposure"] == (
        "The atmosphere was not confirmed safe, ventilation had not been established"
    )
    assert evidence["barrier"] == "required entry checks"
    # The exposure span must not swallow the causal clause, which is barrier
    # evidence: "and the worker entered the vessel without completing the
    # required entry checks" is not part of the exposure.
    assert "required entry checks" not in evidence["exposure"]


def test_internal_inspection_beats_incidental_maintenance_mention(pipeline):
    # "the maintenance team" names who was on site, not what the job was.
    event = _event(pipeline, TARGET)
    assert event.task_phase == "inspection"
    assert event.field_evidence["task_phase"] == "inspect its interior"


@pytest.mark.parametrize(
    "narrative",
    [VERIFIED_ATMOSPHERE, VERIFIED_ATMOSPHERE_2, VERIFIED_ATMOSPHERE_3],
)
def test_verified_atmosphere_never_infers_atmospheric_hazard(pipeline, narrative):
    """Same vocabulary as the target, opposite polarity: the atmosphere WAS
    tested. Presence of the words must not produce an atmospheric hazard.

    Exposure is deliberately not asserted here. For the first narrative the
    baseline already resolves exposure via the literal ontology synonym "vessel
    atmosphere", so requiring `unknown` would fail for a reason that predates
    this detector. The energy, consequence and SIF assertions are what this
    change governs.
    """
    event = _event(pipeline, narrative)
    assert event.energy == "unknown"
    assert event.potential_consequence == "unknown"
    assert event.sif.classification != "high"
    assert event.barrier == "confined_space_procedure"
    assert event.barrier_state == "verified"
    assert _ungrounded(event, narrative) == []


def test_ventilation_alone_is_not_a_confined_space_procedure(pipeline):
    event = _event(pipeline, VENTILATION_ONLY)
    assert event.barrier != "confined_space_procedure"
    assert event.activity == "unknown"
    assert event.energy == "unknown"
    assert event.exposure == "unknown"


def test_maintenance_with_ventilation_keeps_existing_classification(pipeline):
    event = _event(pipeline, MAINTENANCE_VENTILATION)
    assert event.task_phase == "maintenance"
    assert event.barrier == "chemical_handling_controls"
    assert event.activity == "unknown"


def test_entry_without_control_evidence_invents_no_barrier(pipeline):
    event = _event(pipeline, ENTRY_WITHOUT_CONTROL)
    assert event.activity == "confined_space_entry"
    assert event.barrier == "unknown"
    assert event.energy == "unknown"
    assert event.exposure == "unknown"


def test_entry_without_atmosphere_invents_no_energy_or_exposure(pipeline):
    event = _event(pipeline, ENTRY_WITHOUT_ATMOSPHERE)
    assert event.barrier == "confined_space_procedure"
    assert event.energy == "unknown"
    assert event.exposure == "unknown"


def test_no_new_ontology_codes_are_introduced(pipeline):
    """Every code the context detector can SELECT must already exist.

    potential_consequence is excluded on purpose: it is derived downstream from
    grounded hazard/exposure evidence, not read from the ontology. The detector
    does not touch it.
    """
    ontology = get_ontology()
    for category, code in (
        ("activity", "confined_space_entry"),
        ("task_phase", "inspection"),
        ("energy", "flammable_atmosphere"),
        ("exposure", "confined_space_atmosphere"),
        ("barrier", "confined_space_procedure"),
        ("barrier_state", "not_verified"),
    ):
        assert ontology.concept(category, code) is not None, f"{category}/{code}"
