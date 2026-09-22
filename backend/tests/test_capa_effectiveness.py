"""CAPA effectiveness engine, repository and API tests (SQLite).

The effectiveness verdicts are DERIVED deterministically from persisted
barrier-state observations before creation vs after closure -- these tests pin
that reproducibility so nobody can regress it into fabricated scoring.
"""

from __future__ import annotations

import datetime as _dt

from app.database import repos
from app.models.capa import CAPA, BaselineSnapshot
from app.models.safety_event import Observation, SafetyEvent


def _iso(days_ago: int) -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=days_ago)
    ).isoformat()


def _barrier_obs(
    report_id: str,
    barrier_state: str,
    days_ago: int,
    barrier: str = "energy_isolation",
    location: str = "pipeline_section",
    sif_consequence: str = "serious_injury_or_fatality",
) -> Observation:
    event = SafetyEvent(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        energy="pressurized_gas",
        barrier=barrier,
        barrier_state=barrier_state,
        exposure="uncontrolled_gas_release",
        location=location,
        potential_consequence=sif_consequence,
        sif={
            "classification": "high" if barrier_state != "verified" else "low",
            "confidence": 0.95,
            "reason": "test",
        },
    )
    obs = Observation(
        report_id=report_id,
        narrative=f"{report_id} barrier {barrier_state} observation",
        event=event,
        created_at=_iso(days_ago),
    )
    return repos.create_observation(obs)


def _make_capa(report_id="CAPA-T1", barrier="energy_isolation", **kw) -> CAPA:
    defaults = dict(
        report_id=report_id,
        title="Introduce mandatory isolation verification checklist.",
        linked_barrier_id=barrier,
        location="pipeline_section",
        site="EAST",
        status="open",
        baseline=BaselineSnapshot(window_days=90),
        created_at=_iso(30),
    )
    defaults.update(kw)
    return repos.create_capa(CAPA(**defaults))


def test_baseline_window_counts_failures_sif_and_sites():
    _barrier_obs("BASE-01", "not_verified", 20, location="pipeline_section")
    _barrier_obs("BASE-02", "not_verified", 10, location="compressor_room")
    _barrier_obs("BASE-03", "verified", 8, location="tank_farm")

    capa = _make_capa(created_at=_iso(5))
    assert capa.status == "open"
    assert capa.effectiveness_status == "under_observation"
    assert capa.baseline.failure_count == 2
    assert capa.baseline.sif_potential_count == 3  # includes verified SIF-low? see below
    assert capa.baseline.affected_sites == 2
    assert set(capa.baseline.observation_ids) == {
        "OBS-BASE-01", "OBS-BASE-02", "OBS-BASE-03",
    }


def test_sif_potential_counts_only_explicit_sif_evidence():
    _barrier_obs("BASE-10", "not_verified", 20, sif_consequence="none_identified")
    capa = _make_capa(created_at=_iso(5))
    assert capa.baseline.sif_potential_count == 0
    assert capa.baseline.failure_count == 1


def test_closed_capa_without_post_evidence_stays_under_observation():
    _barrier_obs("BASE-20", "not_verified", 20)
    capa = _make_capa(created_at=_iso(10))
    closed = repos.update_capa_status(capa.id, "closed", closed_at=_iso(2))
    assert closed.status == "closed"
    assert closed.closed_at is not None
    assert closed.effectiveness_status == "under_observation"
    assert closed.post_capa.observation_ids == []


def test_recurrence_detected_after_close():
    _barrier_obs("BASE-30", "not_verified", 20)
    capa = _make_capa(created_at=_iso(10))
    repos.update_capa_status(capa.id, "closed", closed_at=_iso(5))
    _barrier_obs("POST-30", "not_verified", 1)
    from app.services.capa.effectiveness import recompute_all_effectiveness

    recompute_all_effectiveness()
    rec = repos.get_capa(capa.id)
    assert rec.effectiveness_status == "recurrence_detected"
    assert rec.post_capa.recurrence_count == 1
    assert "OBS-POST-30" in rec.post_capa.recurrence_observation_ids
    # Baseline + post evidence both support the verdict.
    assert "OBS-BASE-30" in rec.evidence_observation_ids
    assert "OBS-POST-30" in rec.evidence_observation_ids


def test_post_closure_recurrence_surfaces_without_manual_recompute():
    """Regression: CAPA-CD28E9D3C4 / OIL-OBS-8047.

    A closed energy-isolation CAPA gains a barrier-failure observation shortly
    after closure (CAPA closed 16:01:11, observation logged 16:02:44). The
    observation is created through the normal analyzer path
    (POST /analyze -> repos.create_observation); the CAPA detail read must then
    show a post-closure recurrence without any manual recompute call.
    """
    capa = repos.create_capa(
        CAPA(
            id="CAPA-CD28E9D3C4",
            report_id="CD28E9D3C4",
            title="Mandatory energy-isolation verification checklist.",
            linked_barrier_id="energy_isolation",
            location="process_area",
            site="EAST",
            status="closed",
            baseline=BaselineSnapshot(window_days=90),
            created_at="2026-09-01T10:00:00Z",
            closed_at="2026-09-22T16:01:11Z",
        )
    )

    event = SafetyEvent(
        activity="pipeline_maintenance",
        task_phase="maintenance",
        energy="pressurized_gas",
        barrier="energy_isolation",
        barrier_state="not_verified",
        exposure="uncontrolled_gas_release",
        location="process_area",
        potential_consequence="serious_injury_or_fatality",
        sif={"classification": "high", "confidence": 0.95, "reason": "fault"},
    )
    repos.create_observation(
        Observation(
            id="OIL-OBS-8047",
            report_id="OBS-8047",
            narrative="Pipeline joint opened without zero-energy verification.",
            event=event,
            created_at="2026-09-22T16:02:44Z",
        )
    )

    rec = repos.get_capa(capa.id)
    assert rec.effectiveness_status == "recurrence_detected"
    assert rec.post_capa.recurrence_count == 1
    assert rec.post_capa.observation_ids == ["OIL-OBS-8047"]
    assert rec.post_capa.recurrence_observation_ids == ["OIL-OBS-8047"]
    assert "OIL-OBS-8047" in rec.evidence_observation_ids

    # CAPA detail API (GET /capas/{id}) serves the same persisted fields.
    from app.api.routes import capa as capa_route

    detail = capa_route.get_capa(capa.id)
    assert detail.effectiveness_status == "recurrence_detected"
    assert detail.post_capa["recurrence_count"] == 1
    assert detail.post_capa["recurrence_observation_ids"] == ["OIL-OBS-8047"]


def test_improvement_observed_with_verified_post_evidence():
    _barrier_obs("BASE-40", "not_verified", 20)
    capa = _make_capa(created_at=_iso(10))
    repos.update_capa_status(capa.id, "closed", closed_at=_iso(5))
    _barrier_obs("POST-40", "verified", 2, location="pipeline_section")
    from app.services.capa.effectiveness import recompute_all_effectiveness

    recompute_all_effectiveness()
    rec = repos.get_capa(capa.id)
    assert rec.effectiveness_status == "improvement_observed"
    assert rec.post_capa.recurrence_count == 0
    assert rec.post_capa.observation_ids == ["OBS-POST-40"]


def test_insufficient_evidence_without_baseline():
    capa = _make_capa(barrier="machinery_guarding", created_at=_iso(10))
    closed = repos.update_capa_status(capa.id, "closed", closed_at=_iso(5))
    _barrier_obs("POST-50", "verified", 2, barrier="machinery_guarding",
                 location="pump_station")
    from app.services.capa.effectiveness import recompute_all_effectiveness

    recompute_all_effectiveness()
    rec = repos.get_capa(capa.id)
    assert rec.effectiveness_status == "insufficient_evidence"
    assert rec.baseline.failure_count == 0
    assert rec.baseline.sif_potential_count == 0


def test_open_capa_is_under_observation_even_with_recent_evidence():
    _barrier_obs("BASE-60", "not_verified", 20)
    capa = _make_capa(created_at=_iso(30))
    assert capa.effectiveness_status == "under_observation"


def test_recompute_is_idempotent_and_persists_snapshots():
    _barrier_obs("BASE-70", "not_verified", 20)
    capa = _make_capa(created_at=_iso(10))
    repos.update_capa_status(capa.id, "closed", closed_at=_iso(5))
    _barrier_obs("POST-70", "not_verified", 1)
    from app.services.capa.effectiveness import recompute_all_effectiveness

    first = recompute_all_effectiveness()
    after = repos.get_capa(capa.id)
    second = recompute_all_effectiveness()
    again = repos.get_capa(capa.id)
    assert first >= 1 and second >= 1
    assert after.effectiveness_status == "recurrence_detected"
    assert after.baseline.failure_count == again.baseline.failure_count
    assert after.evidence_observation_ids == again.evidence_observation_ids


def test_empty_report_id_creates_unique_capas():
    a = _make_capa(report_id="", created_at=_iso(5))
    b = _make_capa(report_id="", created_at=_iso(4))
    assert a.id != b.id
    assert repos.count_capas() == 2


def test_capa_crud_repos_round_trip():
    capa = _make_capa(created_at=_iso(5))
    assert repos.get_capa(capa.id).id == capa.id
    assert repos.get_capa_by_report_id("CAPA-T1").id == capa.id
    assert repos.count_capas() == 1
    assert [c.id for c in repos.list_capas()] == [capa.id]
    assert repos.delete_capa(capa.id) is True
    assert repos.get_capa(capa.id) is None
    assert repos.delete_capa(capa.id) is False


def test_capa_route_create_status_get_list_delete():
    from app.schemas.api import CapaCreate, CapaStatusUpdate
    from app.api.routes import capa as capa_route

    _barrier_obs("BASE-80", "not_verified", 20)
    created = capa_route.create_capa(
        CapaCreate(
            report_id="R-ROUTE-01",
            title="Route created isolation checklist",
            linked_barrier_id="energy_isolation",
            location="pipeline_section",
            site="EAST",
            status="open",
            created_at=_iso(8),
        )
    )
    assert created.effectiveness_status == "under_observation"
    assert created.baseline["failure_count"] == 1

    listed = capa_route.list_capas(
        status="open", linked_barrier_id=None, limit=100, offset=0
    )
    assert any(c.id == created.id for c in listed["capas"])
    single = capa_route.get_capa(created.id)
    assert single.id == created.id

    closed = capa_route.update_capa_status(
        created.id, CapaStatusUpdate(status="closed", closed_at=_iso(2))
    )
    assert closed.closed_at is not None
    filtered = capa_route.list_capas(
        status="closed", linked_barrier_id=None, limit=100, offset=0
    )
    assert any(c.id == created.id for c in filtered["capas"])

    assert capa_route.delete_capa(created.id) is None
    try:
        capa_route.delete_capa(created.id)
    except Exception as exc:  # noqa: BLE001 - route raises HTTPException 404
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("expected 404 for missing capa")


def test_capa_route_unknown_status_and_barrier_filters():
    from app.api.routes import capa as capa_route

    _make_capa(report_id="F-A", barrier="energy_isolation", created_at=_iso(6))
    _make_capa(report_id="F-B", barrier="hot_work_controls", created_at=_iso(5),
               site="WEST", location="workshop")
    barrier_filtered = capa_route.list_capas(
        status=None, linked_barrier_id="energy_isolation", limit=100, offset=0
    )
    assert len(barrier_filtered["capas"]) == 1
    assert barrier_filtered["total"] == 1
    assert capa_route.list_capas(
        status="open", linked_barrier_id=None, limit=100, offset=0
    )["total"] == 2


def test_capa_route_get_missing_404():
    from fastapi import HTTPException

    from app.api.routes import capa as capa_route

    try:
        capa_route.get_capa("CAPA-NOPE")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected 404")


def test_capa_demo_seed_produces_all_four_verdicts():
    from app.services.demo.capa_seed import seed_capa_demo

    result = seed_capa_demo()
    assert result["observations_seeded"] == 7
    assert result["capas_seeded"] == 4
    by_id = {c["id"]: c for c in result["capas"]}
    assert by_id["CAPA-CAPA-RECUR-01"]["effectiveness_status"] == "recurrence_detected"
    assert by_id["CAPA-CAPA-IMPR-01"]["effectiveness_status"] == "improvement_observed"
    assert by_id["CAPA-CAPA-OBS-01"]["effectiveness_status"] == "under_observation"
    assert by_id["CAPA-CAPA-INSUF-01"]["effectiveness_status"] == "insufficient_evidence"

    # The headline PRD scenario: three baseline isolation failures, CAPA closed,
    # a fresh "not verified before opening the line" observation -> recurrence.
    rec = repos.get_capa("CAPA-CAPA-RECUR-01")
    assert rec is not None
    assert rec.baseline.failure_count == 3
    assert rec.post_capa.recurrence_count == 1
    assert "CAPAP-01" in " ".join(rec.post_capa.recurrence_observation_ids)
    assert rec.effectiveness_basis["baseline"]["_counted"] >= 3


def test_capa_seed_is_idempotent():
    from app.services.demo.capa_seed import seed_capa_demo

    seed_capa_demo()
    seed_capa_demo()
    assert repos.count_capas() == 4
    assert repos.count_observations() == 7