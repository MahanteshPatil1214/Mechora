"""Extraction precedence regressions.

Two explicit-wording cases where a *general* canonical value used to win over a
more specific one that the narrative actually named:

* ``task_phase`` — a known activity forced ``maintenance`` even when the
  narrative explicitly framed the observation as the PRE-JOB phase
  ("Pre-job: ...", "prior to ...", "before work started").
* ``barrier`` — the generic ``work_permit`` barrier shadowed an explicitly
  named ``hot_work_controls`` control (only possible because "hot work permit"
  was ALSO a work_permit synonym, and because a non-failing hot-work match lost
  the state-weight scoring).

These pin the precedence, not the wording: each assertion is paired with a
near-miss that must stay on the general value.
"""

from __future__ import annotations

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline


def _event(narrative: str):
    return AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "PREC-1", narrative, provider="rules"
    ).event


# ------------------------------------------------------------- task_phase

def test_explicit_pre_job_phase_wins_over_known_activity():
    # "gas lift manifold" resolves an activity, but the observation is about
    # the pre-job verification step, so pre_job must win.
    narrative = (
        "During routine maintenance on the gas lift manifold, the fitter "
        "loosened a joint without prior zero-energy verification; gas "
        "escaped."
    )
    ev = _event(narrative)
    assert ev.activity == "pipeline_maintenance"
    assert ev.task_phase == "pre_job"
    assert ev.field_evidence["task_phase"]


def test_explicit_pre_job_phase_wins_over_incidental_maintenance():
    # Activity is unknown and the ontology incidentally matches "maintenance";
    # the explicit "Pre-job:" cue must still take precedence.
    narrative = (
        "Pre-job: zero energy verification was not completed before "
        "maintenance on the gas line; gas leaked."
    )
    ev = _event(narrative)
    assert ev.task_phase == "pre_job"


def test_activity_implied_maintenance_still_defaults_to_maintenance():
    # No explicit pre-job phase -> the known activity still implies maintenance.
    narrative = (
        "During routine flange tightening on the gas line, the fitter did not "
        "confirm zero energy before loosening the joint and gas released."
    )
    ev = _event(narrative)
    assert ev.activity == "pipeline_maintenance"
    assert ev.task_phase == "maintenance"


# --------------------------------------------------------------- barrier

def test_explicit_hot_work_controls_beat_work_permit():
    # Both barriers are named; the specific hot-work control must win.
    narrative = (
        "Hot work controls were not in place before welding, and the work "
        "permit was not issued."
    )
    ev = _event(narrative)
    assert ev.barrier == "hot_work_controls"


def test_hot_work_permit_maps_to_hot_work_controls():
    # "hot work permit" belongs to the hot-work control set, never the generic
    # work-permit barrier.
    narrative = (
        "The hot work permit was not obtained before welding on the pipeline; "
        "no gas test was done."
    )
    ev = _event(narrative)
    assert ev.barrier == "hot_work_controls"


def test_generic_work_permit_stays_work_permit():
    # A plain permit failure with no hot-work control named stays work_permit.
    narrative = "Work permit was not approved and gas escaped during hot work."
    ev = _event(narrative)
    assert ev.barrier == "work_permit"
