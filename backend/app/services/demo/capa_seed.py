"""Deterministic CAPA Effectiveness demo dataset.

``seed_capa_demo()`` performs an EXPLICIT reset (observations, precursor
families and CAPA rows) and seeds a small, self-contained dataset that walks
the three supporting observation reports from the effectiveness PRD through the
system:

    Observation 1: Energy isolation not verified.
    Observation 2: Isolation verification missing.
    Observation 3: LOTO verification incomplete.
    -> CAPA: "Introduce mandatory isolation verification checklist." (closed)
    -> New observation: "Energy isolation was not verified before opening the
       line."  -> POST-CAPA RECURRENCE DETECTED.

A second closed CAPA (hot-work controls) shows EVIDENCE OF IMPROVEMENT when a
verified post-closure control observation exists with zero recurrences, plus an
open CAPA (UNDER OBSERVATION) and a closed CAPA with no baseline evidence to
compare (INSUFFICIENT EVIDENCE).

Timestamps are relative to "now" so the fixed ``window_days=120`` baseline
window always contains the seeded evidence regardless of when the seed runs.
All ids are deterministic (report-id based), so re-seeding is idempotent.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import delete

from app.database.engine import dispose, get_session, init_db
from app.database.repos import new_capa_id, new_observation_id
from app.database.tables import CAPARow, ObservationRow, PrecursorFamilyRow
from app.models.capa import CAPA, BaselineSnapshot
from app.models.safety_event import Observation, SafetyEvent

# Wider than the app default (90d) so the seeded windows are self-contained
# even when relative timestamps drift a little between seed cycles.
WINDOW_DAYS = 120


def _iso(days_ago: int) -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=days_ago)
    ).isoformat()


def _observation(
    report_id: str,
    narrative: str,
    barrier: str,
    barrier_state: str,
    location: str,
    days_ago: int,
    energy: str = "pressurized_gas",
    exposure: str = "uncontrolled_gas_release",
) -> Observation:
    event = SafetyEvent(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        energy=energy,
        barrier=barrier,
        barrier_state=barrier_state,
        exposure=exposure,
        location=location,
        potential_consequence=(
            "serious_injury_or_fatality"
            if barrier_state != "verified"
            else "unknown"
        ),
        field_evidence={"barrier": barrier, "barrier_state": barrier_state},
        precursor_signature={
            "energy": energy,
            "barrier": barrier,
            "barrier_state": barrier_state,
            "exposure": exposure,
            "task_phase": "maintenance",
            "activity": "pipeline_maintenance",
            "potential_consequence": (
                "serious_injury_or_fatality"
                if barrier_state != "verified"
                else "unknown"
            ),
        },
    )
    obs = Observation(
        report_id=report_id,
        narrative=narrative,
        event=event,
        created_at=_iso(days_ago),
    )
    obs.id = new_observation_id(report_id)
    return obs


def _capa(
    report_id: str,
    title: str,
    barrier: str,
    status: str,
    created_days_ago: int,
    closed_days_ago: int | None = None,
    site: str = "EAST",
    location: str = "process_area",
) -> CAPA:
    capa = CAPA(
        report_id=report_id,
        title=title,
        description=(
            "Seeded CAPA effectiveness demonstration. Decision support only; "
            "not accident prediction."
        ),
        linked_barrier_id=barrier,
        location=location,
        site=site,
        status=status,
        baseline=BaselineSnapshot(window_days=WINDOW_DAYS),
        created_at=_iso(created_days_ago),
        closed_at=_iso(closed_days_ago) if closed_days_ago is not None else None,
    )
    capa.id = new_capa_id(report_id)
    return capa


def seed_capa_demo() -> dict:
    """Reset and seed the self-contained CAPA effectiveness demo dataset.

    Explicit reset (observations + families + capa rows) so the four verdicts
    below are byte-deterministic. Returns a summary dict for CLI / tests.
    """
    from app.database import repos

    dispose()
    init_db()
    with get_session() as s:
        s.execute(delete(CAPARow))
        s.execute(delete(PrecursorFamilyRow))
        s.execute(delete(ObservationRow))
        s.commit()

    observations = [
        # --- Baseline: common barrier ENERGY_ISOLATION failures ------------
        _observation(
            "CAPAB-01",
            "Energy isolation not verified before the joint was loosened "
            "on the gas line.",
            "energy_isolation", "not_verified", "pipeline_section", 18,
        ),
        _observation(
            "CAPAB-02",
            "Isolation verification missing before flange work on the "
            "compressor loop.",
            "energy_isolation", "not_verified", "compressor_room", 15,
        ),
        _observation(
            "CAPAB-03",
            "LOTO verification incomplete during line opening in the "
            "process area.",
            "energy_isolation", "not_verified", "process_area", 12,
        ),
        # --- Baseline: HOT_WORK_CONTROLS failures (improvement scenario) ----
        _observation(
            "CAPAB-H1",
            "Gas test skipped before grinding started in the workshop.",
            "hot_work_controls", "not_verified", "workshop", 20,
            energy="flammable_atmosphere", exposure="fire_or_explosion",
        ),
        _observation(
            "CAPAB-H2",
            "Hot work completed without atmospheric testing at the tank farm.",
            "hot_work_controls", "not_verified", "tank_farm", 14,
            energy="flammable_atmosphere", exposure="fire_or_explosion",
        ),
        # --- Post-closure RECURRENCE evidence -------------------------------
        _observation(
            "CAPAP-01",
            "Energy isolation was not verified before opening the line.",
            "energy_isolation", "not_verified", "pipeline_section", 2,
        ),
        # --- Post-closure VERIFIED control evidence (improvement scenario) --
        _observation(
            "CAPAP-H1",
            "Gas testing completed and atmosphere confirmed safe before "
            "grinding started.",
            "hot_work_controls", "verified", "workshop", 1,
            energy="flammable_atmosphere", exposure="unknown",
        ),
    ]
    for obs in observations:
        repos.create_observation(obs)

    capas = [
        # 1. RECURRENCE DETECTED: closed with a fresh energy-isolation failure.
        _capa(
            "CAPA-RECUR-01",
            "Introduce mandatory isolation verification checklist.",
            "energy_isolation", "closed",
            created_days_ago=10, closed_days_ago=5,
        ),
        # 2. EVIDENCE OF IMPROVEMENT: closed with verified post-closure controls.
        _capa(
            "CAPA-IMPR-01",
            "Mandatory gas testing before every hot work job.",
            "hot_work_controls", "closed",
            created_days_ago=8, closed_days_ago=4,
            site="WEST", location="workshop",
        ),
        # 3. UNDER OBSERVATION: still open, baseline evidence present.
        _capa(
            "CAPA-OBS-01",
            "Review energy isolation training compliance across crews.",
            "energy_isolation", "open",
            created_days_ago=3,
        ),
        # 4. INSUFFICIENT EVIDENCE: closed with no baseline to compare.
        _capa(
            "CAPA-INSUF-01",
            "Review machinery guarding on the transfer pumps.",
            "machinery_guarding", "closed",
            created_days_ago=9, closed_days_ago=6,
            site="WEST", location="pump_station",
        ),
    ]
    for capa in capas:
        repos.create_capa(capa)

    return {
        "observations_seeded": len(observations),
        "capas_seeded": len(capas),
        "capas": [
            {
                "id": c.id,
                "title": c.title,
                "linked_barrier": c.linked_barrier_id,
                "status": c.status,
                "effectiveness_status": c.effectiveness_status,
            }
            for c in repos.list_capas(limit=100)
        ],
    }