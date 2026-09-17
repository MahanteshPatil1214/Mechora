"""Structural weights for precursor similarity (PRD section 12).

Prototype engineering parameters, not official OIL risk weights. Configurable
through ``STRUCTURAL_WEIGHTS`` and overridable via settings.
"""

STRUCTURAL_WEIGHTS: dict[str, float] = {
    "barrier": 0.20,  # barrier code match
    "barrier_state": 0.10,  # state match (verified != not_verified)
    "energy": 0.25,  # hazard / energy dimension
    "exposure": 0.20,
    "task_phase": 0.15,
    "activity": 0.10,
}

# barrier + barrier_state must total 0.30 per the PRD prototype table.
assert abs(STRUCTURAL_WEIGHTS["barrier"] + STRUCTURAL_WEIGHTS["barrier_state"]
           - 0.30) < 1e-9

SIGNATURE_FIELDS = (
    "activity",
    "task_phase",
    "energy",
    "barrier",
    "barrier_state",
    "exposure",
    "potential_consequence",
)

MISSING = {"", "unknown", "needs_review", "none_identified"}

BARRIER_FIELD = "barrier"
STATE_FIELD = "barrier_state"


def get_weights() -> dict[str, float]:
    return dict(STRUCTURAL_WEIGHTS)