"""CAPA effectiveness derivation engine (deterministic, evidence-anchored).

NEVER fabricates a score. Every ``effectiveness_*`` value is DERIVED by
recomputing reproducible evidence windows from **persisted** observations for
the CAPA's linked barrier:

* ``baseline``  : barrier-state evidence in the ``window_days`` BEFORE the CAPA
                  was created  ->  ``failure_count``, ``sif_potential_count``,
                  ``affected_sites``, ``observation_ids``.
* ``post_capa`` : only after a CAPA is CLOSED --- barrier-state evidence in the
                  ``window_days`` AFTER ``closed_at``  ->  ``recurrence_count``,
                  ``observation_ids``, ``recurrence_observation_ids``.

``effectiveness_status`` is then derived from those two reproducible windows:

* ``under_observation``     : CAPA not yet closed, OR closed so recently that
                              the post-closure window holds no observations yet
                              (evidence is still being gathered).
* ``insufficient_evidence`` : CAPA closed but the baseline shows no barrier
                              failure and no SIF-potential evidence to compare
                              against, so no improvement can be claimed.
* ``recurrence_detected``   : >=1 barrier-state failure recurred after close.
* ``improvement_observed``  : baseline had failures and post-closure evidence
                              exists with zero recurrences (a leading indicator
                              that the barrier no longer fails; never a claim
                              that an accident was prevented).

NOTE: ``repos.apply_observation_filters`` does not clamp on
``created_before/created_after`` in SQL, so all time-windowing happens here in
Python over ISO-8601 ``created_at`` strings for exact reproducibility.
"""

from __future__ import annotations

import datetime as _dt

from app.database import repos
from app.models.capa import (
    BARRIER_FAILURE_STATES,
    BaselineSnapshot,
    CAPA,
    PostCAPASnapshot,
)

# Barrier-state codes that constitute a barrier *failure* (a hole in the safety
# net that the CAPA exists to close). Mirrors models/safety_event.py failure
# literals; anything not in this set (verified/unknown) is NOT counted.
BARRIER_FAILURE_STATES = BARRIER_FAILURE_STATES


def _iso(ts: str) -> _dt.datetime:
    """Parse an ISO-8601 timestamp produced by ``models._now()``.

    Accepts both ``+00:00`` and ``Z`` suffixes. Falls back to ``datetime.min``
    (never raises) so a malformed timestamp yields an empty window rather than
    crashing the recompute pass.
    """
    if not ts:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    raw = ts.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        d = _dt.datetime.fromisoformat(raw)
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return d
    except ValueError:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)


def _fmt(d: _dt.datetime) -> str:
    return d.astimezone(_dt.timezone.utc).isoformat()


def _barrier_failed(obs) -> bool:
    """A barrier-state observation is a *failure* iff its barrier_state is a
    canonical failure code (not verified / failed / absent / partially
    effective). Verified and unknown states never count as failures."""
    return (getattr(obs.event, "barrier_state", "") or "unknown") in (
        BARRIER_FAILURE_STATES
    )


def _sif_potential(obs) -> bool:
    """SIF-potential evidence for a barrier-state observation.

    Counts only explicit SIF evidence: either the caller/environment flagged
    ``sif_potential`` on the event, or the event already carries a SIF
    ``potential_consequence`` that is severity-scored at intake. Never inferred
    here from narrative word lists --- if the persisted event has no SIF
    potential, the count stays at zero (honest, reproducible).
    """
    ev = obs.event
    sip = getattr(ev, "sif_potential", None)
    if sip:
        return True
    conseq = getattr(ev, "potential_consequence", "") or ""
    return conseq in (
        "serious_injury_or_fatality",
        "serious_injury_or_fatality_likely",
        "fatality",
        "major_accident",
    )


def _window_observations(
    barrier: str,
    window_days: int,
    anchor_lte: str,
    anchor_gt: str,
) -> list:
    """Barrier-state observations whose ``created_at`` is strictly greater than
    ``anchor_gt`` and less-than-or-equal ``anchor_lte`` (the closed ``(after,
    before]`` evidence window). Window is applied in Python so it is exact
    regardless of SQL backend ordering of ``ObservationFilters`` (which does
    not clamp time)."""
    rows = []
    for o in repos.list_observations(
        repos.ObservationFilters(barrier=barrier, limit=1000)
    ):
        t = _iso(o.created_at)
        if _iso(anchor_gt) < t <= _iso(anchor_lte):
            rows.append(o)
    return rows


def _baseline_snapshot(
    barrier: str, capa_created_at: str, window_days: int
) -> tuple[BaselineSnapshot, dict]:
    before = _iso(capa_created_at)
    after = before - _dt.timedelta(days=window_days)
    obs = _window_observations(barrier, window_days, _fmt(before), _fmt(after))
    failures = [o for o in obs if _barrier_failed(o)]
    counts_failures = len(failures)
    sif_count = sum(1 for o in obs if _sif_potential(o))
    sites = sorted({o.event.location for o in failures if o.event.location})
    return (
        BaselineSnapshot(
            barrier=barrier,
            barrier_state="failed" if counts_failures else "not_verified" if obs else "unknown",
            window_days=window_days,
            from_iso=_fmt(after),
            to_iso=_fmt(before),
            failure_count=counts_failures,
            sif_potential_count=sif_count,
            affected_sites=len(sites),
            observation_ids=[o.id for o in obs],
        ),
        {"window_days": window_days, "counted_observations": len(obs)},
    )


def _post_capa_snapshot(
    barrier: str, closed_at: str, window_days: int
) -> tuple[PostCAPASnapshot, dict]:
    after = _iso(closed_at)
    until = after + _dt.timedelta(days=window_days)
    obs = _window_observations(barrier, window_days, _fmt(until), _fmt(after))
    recurrences = [o for o in obs if _barrier_failed(o)]
    return (
        PostCAPASnapshot(
            barrier=barrier,
            barrier_state="failed" if recurrences else "verified" if obs else "unknown",
            window_days=window_days,
            from_iso=_fmt(after),
            to_iso=_fmt(until),
            recurrence_count=len(recurrences),
            recurrence_observation_ids=[o.id for o in recurrences],
            observation_ids=[o.id for o in obs],
        ),
        {"window_days": window_days, "counted_observations": len(obs)},
    )


def _derive_status(
    capa: CAPA, baseline: BaselineSnapshot, post: PostCAPASnapshot
) -> str:
    """Deterministic effectiveness verdict from the two evidence windows.

    Rules (in priority order):

    1. ``under_observation``  -- CAPA not closed yet, or closed so recently
       that the post-closure window contains NO observations to judge.
    2. ``recurrence_detected`` -- the same barrier failure recurred after close.
    3. ``improvement_observed`` -- a real baseline failure existed AND post
       evidence showed zero recurrences (leading indicator only).
    4. ``insufficient_evidence`` -- nothing to compare before vs after.
    """
    if capa.status != "closed" or not capa.closed_at:
        return "under_observation"
    if post.recurrence_count > 0:
        return "recurrence_detected"
    if baseline.failure_count > 0 or baseline.sif_potential_count > 0:
        # Baseline evidence exists. Only claim improvement once the post
        # window actually contains observations that were evaluated; with zero
        # post-closure evidence we stay in under_observation (evidence pending).
        if post.observation_ids:
            return "improvement_observed"
        return "under_observation"
    return "insufficient_evidence"


def recompute_capa_effectiveness(capa: CAPA) -> CAPA:
    """Recompute the *derived, evidence-backed* effectiveness fields for a
    single CAPA and persist them via ``repos.update_capa_effectiveness``.

    Pure and reproducible: given the same persisted observations, the same
    CAPA fields and the same windows, the result is byte-identical. No LLM, no
    random number generation, no fabrication of basis text.
    """
    window_days = int(capa.baseline.window_days or 90)
    barrier = capa.linked_barrier_id

    baseline, binfo = _baseline_snapshot(barrier, capa.created_at, window_days)

    post = PostCAPASnapshot()
    post_info: dict = {}
    if capa.status == "closed" and capa.closed_at:
        post, post_info = _post_capa_snapshot(barrier, capa.closed_at, window_days)

    status = _derive_status(capa, baseline, post)

    basis = {
        "window_days": window_days,
        "linked_barrier": barrier,
        "status_rule": (
            "CAPA not closed or post-closure window has no observations yet"
            if status == "under_observation" and capa.status == "closed"
            else "CAPA is still in progress (not closed); awaiting closure"
            if status == "under_observation"
            else ">=1 barrier-state failure recurred after CAPA closure"
            if status == "recurrence_detected"
            else (
                "Baseline barrier failure(s) existed and post-closure evidence "
                "shows zero recurrences"
            )
            if status == "improvement_observed"
            else (
                "No baseline barrier failure or SIF-potential evidence to "
                "compare against after closure"
            )
        ),
        "baseline": {
            **baseline.model_dump(mode="json"),
            "_counted": binfo.get("counted_observations", 0),
        },
        "post_capa": {
            **post.model_dump(mode="json"),
            "_counted": post_info.get("counted_observations", 0),
        },
        "derivation": (
            "Derived deterministically from persisted barrier-state "
            "observations in the baseline (pre-creation) and post-closure "
            "windows. Decision support only; not accident prediction."
        ),
    }
    evidence_ids = baseline.observation_ids + post.observation_ids

    return repos.update_capa_effectiveness(
        capa_id=capa.id,
        effectiveness_status=status,
        effectiveness_basis=basis,
        baseline=baseline.model_dump(mode="json"),
        post_capa=post.model_dump(mode="json"),
        evidence_observation_ids=evidence_ids,
    )


def recompute_all_effectiveness() -> int:
    """Recompute + persist effectiveness for every persisted CAPA in one
    deterministic pass. Returns the number of CAPAs updated.

    Called by ``repos.create_capa`` after insert/merge so the API and
    dashboard always serve precomputed, reproducible values."""
    updated = 0
    for capa in repos.list_capas(limit=1000):
        resolved = recompute_capa_effectiveness(capa)
        if resolved is not None:
            updated += 1
    return updated