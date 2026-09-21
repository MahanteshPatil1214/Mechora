"""Exposure normalization regressions.

Guards the canonical exposure vocabulary: steam releases must not be filed as
gas releases, generic "was released" / "leak" wording must not manufacture a gas
exposure, and the existing gas / liquid / electrical / chemical / fire / fall
mappings must stay unchanged.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.models.safety_event import EXPOSURE_CODES
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

STEAM_NARRATIVE = (
    "During pipeline maintenance at the Pump Station, technicians opened a "
    "pressurized steam line before verifying the energy isolation. The isolation "
    "valve had not been verified, and residual steam was released unexpectedly "
    "when the flange was loosened, exposing the technician to a high-energy steam "
    "release with potential for serious injury or fatality."
)


def _exposure(report_id: str, narrative: str) -> str:
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    return pipeline.analyze(report_id, narrative, provider="rules").event.exposure


def test_steam_release_normalizes_to_uncontrolled_steam_release() -> None:
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    event = pipeline.analyze("STEAM-1", STEAM_NARRATIVE, provider="rules").event
    assert event.activity == "pipeline_maintenance"
    assert event.task_phase == "maintenance"
    assert event.energy == "thermal_energy"
    assert event.barrier == "energy_isolation"
    assert event.barrier_state == "not_verified"
    assert event.exposure == "uncontrolled_steam_release"
    assert event.potential_consequence == "serious_injury_or_fatality"
    assert event.location == "pump_station"


@pytest.mark.parametrize(
    "narrative",
    [
        "Residual steam was released unexpectedly when the flange was loosened.",
        "Pressurized steam escaped from the line during maintenance.",
        "A steam leak was found on the steam line at the pump station.",
        "High-pressure steam was released from the ruptured gasket.",
    ],
)
def test_steam_phrasings_map_to_steam(narrative: str) -> None:
    assert _exposure("STEAM-X", narrative) == "uncontrolled_steam_release"


@pytest.mark.parametrize(
    "narrative",
    [
        "During pipeline maintenance the joint was opened and gas was released.",
        "A gas release occurred during pipeline maintenance.",
        "Gas was heard leaking from the flange during maintenance.",
        "Gas leaked out from the compressor casing.",
        "A hydrocarbon release occurred while the valve was opened.",
    ],
)
def test_gas_phrasings_still_map_to_gas(narrative: str) -> None:
    assert _exposure("GAS-X", narrative) == "uncontrolled_gas_release"


def test_steam_and_gas_are_not_confused() -> None:
    assert _exposure("S", "Steam was released unexpectedly.") == (
        "uncontrolled_steam_release"
    )
    assert _exposure("G", "Gas was released from the flange.") == (
        "uncontrolled_gas_release"
    )


@pytest.mark.parametrize(
    "narrative",
    [
        "During pipeline maintenance, the pressure was released and confirmed zero.",
        "The pressure was released and the reading was confirmed zero.",
    ],
)
def test_generic_release_without_substance_is_not_a_gas_exposure(
    narrative: str,
) -> None:
    assert _exposure("GEN-X", narrative) != "uncontrolled_gas_release"


@pytest.mark.parametrize(
    ("narrative", "expected"),
    [
        ("Slurry was released onto the deck after the valve failed.",
         "uncontrolled_liquid_release"),
        ("While working near an energized panel, a live terminal was exposed.",
         "electrical_shock_risk"),
        ("Fume inhalation occurred during tank work when the hatch was opened.",
         "chemical_contact"),
        ("A flash fire occurred during hot work at the tank.",
         "fire_or_explosion"),
        ("The worker slipped from the platform and had a fall from height.",
         "fall_from_height"),
    ],
)
def test_existing_exposure_mappings_unchanged(
    narrative: str, expected: str
) -> None:
    assert _exposure("EXIST-X", narrative) == expected


def test_exposure_codes_match_ontology_schema() -> None:
    """The Pydantic Literal and the ontology vocabulary must not drift."""
    literal_codes = {a for a in getattr(EXPOSURE_CODES, "__args__", ())
                     if isinstance(a, str)}
    ontology_codes = set(get_ontology().codes("exposure"))
    assert ontology_codes == literal_codes
