"""Prototype HSE Attention Signal (FR-11 / PRD section 17).

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

ATTENTION_DISCLAIMER = (
    "Prototype HSE Attention Signal — decision support, "
    "not an official OIL risk score or accident prediction."
)

# Only factors that actually contribute a meaningful lift are reported in
# the basis list (prereq: no empty slideware factors).
FACTOR_MIN_CONTRIBUTION = 0.02  # on the 0..1 normalized scale


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def compute_attention(observations: list[Observation],
                      weights: dict[str, float] | None = None) -> dict:
    """Return {score, basis, factors} for a family of observations.

    ``basis`` only lists factors whose normalized contribution exceeds
    ``FACTOR_MIN_CONTRIBUTION``; ``factors`` carries the full transparent
    breakdown (factor, weight, observed value, contribution).
    """
    w = dict(ATTENTION_WEIGHTS if weights is None else weights)
    n = max(len(observations), 1)
    basis: list[str] = []
    factors: list[dict] = []

    def _add(factor: str, value: float, line: str,
             basis_ok: bool = True) -> None:
        contribution = w.get(factor, 0.0) * value
        factors.append({
            "factor": factor,
            "weight": w.get(factor, 0.0),
            "value": round(value, 4),
            "contribution": round(contribution, 4),
        })
        if basis_ok and contribution >= FACTOR_MIN_CONTRIBUTION:
            basis.append(line)

    recurrence = _clamp(math.log2(n + 1) / math.log2(21.0))
    _add("recurrence", recurrence,
         f"Recurrence: {len(observations)} observation(s)",
         basis_ok=len(observations) >= 2)

    failures = [o for o in observations
                if o.event.barrier_state in BARRIER_FAILURE_STATES]
    barrier_failure = len(failures) / n
    _add("barrier_failure", barrier_failure,
         f"Failed-barrier frequency: {len(failures)}/{n}")

    exposure_ranks = [
        _severity("exposure", o.event.exposure) for o in observations
    ]
    exposure = _clamp((max(exposure_ranks, default=1) - 1) / 4.0)
    _add("exposure", exposure,
         f"Max exposure severity: {max(exposure_ranks, default=1):.0f}/5")

    activities = {o.event.activity for o in observations
                  if o.event.activity not in ("unknown", "")}
    cross_activity = _clamp(len(activities) / 4.0)
    _add("cross_activity", cross_activity,
         f"Cross-activity occurrence: {len(activities)} distinct")

    sif_high = [o for o in observations
                if o.event.sif.classification in ("high", "medium")]
    sif_evidence = len(sif_high) / n
    _add("sif_evidence", sif_evidence,
         f"SIF-potential observations: {len(sif_high)}/{n}")

    energy_ranks = [_severity("energy", o.event.energy) for o in observations]
    energy_severity = _clamp((max(energy_ranks, default=1) - 1) / 4.0)
    _add("energy_severity", energy_severity,
         f"Max energy severity: {max(energy_ranks, default=1):.0f}/5")

    score = 100.0 * sum(f["contribution"] for f in factors)
    return {
        "score": round(_clamp(score, 0.0, 100.0), 2),
        "basis": basis,
        "factors": factors,
    }


def _severity(kind: str, code: str) -> float:
    if not code or code == "unknown":
        return 1.0
    from app.services.normalization.ontology import get_ontology
    onto = get_ontology()
    if kind == "energy":
        return float(onto.energy_rank(code))
    return float(onto.exposure_rank(code))