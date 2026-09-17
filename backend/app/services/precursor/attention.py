"""Prototype Precursor Attention Signal (FR-11 / PRD section 17).

A configurable 0-100 prototype signal. It MUST NOT be presented as an official
OIL risk score. Inputs: recurrence, barrier-failure frequency, exposure
characteristics, cross-activity occurrence and SIF-potential evidence.
"""

from __future__ import annotations

import math

from app.models.safety_event import BARRIER_FAILURE_STATES, Observation

ATTENTION_WEIGHTS: dict[str, float] = {
    "recurrence": 0.25,
    "barrier_failure": 0.20,
    "exposure": 0.20,
    "cross_activity": 0.15,
    "sif_evidence": 0.15,
    "energy_severity": 0.05,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def compute_attention(observations: list[Observation],
                      weights: dict[str, float] | None = None) -> dict:
    """Return {score, basis} for a family of observations."""
    w = dict(ATTENTION_WEIGHTS if weights is None else weights)
    n = max(len(observations), 1)
    basis: list[str] = []

    recurrence = _clamp(math.log2(n + 1) / math.log2(21.0))
    basis.append(f"recurrence: {len(observations)} observation(s)")

    failures = [o for o in observations
                if o.event.barrier_state in BARRIER_FAILURE_STATES]
    barrier_failure = len(failures) / n
    basis.append(f"barrier failure frequency: {len(failures)}/{n}")

    exposure_ranks = [
        _severity("exposure", o.event.exposure) for o in observations
    ]
    exposure = _clamp((max(exposure_ranks, default=1) - 1) / 4.0)
    basis.append(f"max exposure severity: {max(exposure_ranks, default=1):.0f}/5")

    activities = {o.event.activity for o in observations
                  if o.event.activity not in ("unknown", "")}
    cross_activity = _clamp(len(activities) / 4.0)
    basis.append(f"cross-activity occurrence: {len(activities)} distinct")

    sif_high = [o for o in observations
                if o.event.sif.classification in ("high", "medium")]
    sif_evidence = len(sif_high) / n
    basis.append(f"SIF-potential observations: {len(sif_high)}/{n}")

    energy_ranks = [_severity("energy", o.event.energy) for o in observations]
    energy_severity = _clamp((max(energy_ranks, default=1) - 1) / 4.0)

    score = 100.0 * (
        w["recurrence"] * recurrence
        + w["barrier_failure"] * barrier_failure
        + w["exposure"] * exposure
        + w["cross_activity"] * cross_activity
        + w["sif_evidence"] * sif_evidence
        + w["energy_severity"] * energy_severity
    )
    return {
        "score": round(_clamp(score, 0.0, 100.0), 2),
        "basis": basis,
    }


def _severity(kind: str, code: str) -> float:
    if not code or code == "unknown":
        return 1.0
    from app.services.normalization.ontology import get_ontology
    onto = get_ontology()
    if kind == "energy":
        return float(onto.energy_rank(code))
    return float(onto.exposure_rank(code))