"""Precursor signature generation & structural similarity.

The signature is the machine-comparable structural tuple used by the precursor
engine. Similarity is a weighted per-dimension match; embeddings may only be a
supporting signal and are optional.
"""

from __future__ import annotations

import math

from app.models.safety_event import PrecursorSignature, SafetyEvent
from app.services.precursor.weights import (
    BARRIER_FIELD,
    MISSING,
    SIGNATURE_FIELDS,
    STATE_FIELD,
    get_weights,
)


def build_signature(event: SafetyEvent) -> PrecursorSignature:
    return PrecursorSignature(
        activity=_sig(event.activity),
        task_phase=_sig(event.task_phase),
        energy=_sig(event.energy),
        barrier=event.barrier if event.barrier else "unknown",
        barrier_state=event.barrier_state if event.barrier_state else "unknown",
        exposure=_sig(event.exposure),
        potential_consequence=_sig(event.potential_consequence),
    )


def _sig(value: str) -> str:
    return value or "unknown"


def signature_tuple(sig: PrecursorSignature) -> tuple[str, ...]:
    return tuple(getattr(sig, f) for f in SIGNATURE_FIELDS)


def _known(value: str) -> bool:
    return value not in MISSING


class StructuralSimilarity:
    """Weighted structural similarity between two precursor signatures."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = get_weights() if weights is None else weights

    def score(self, a: PrecursorSignature,
              b: PrecursorSignature, embedding_note: bool = False) -> dict:
        dims: list[dict] = []
        total = 0.0
        max_w = sum(self.weights.values())

        for field, weight in self.weights.items():
            va = _sig(getattr(a, field))
            vb = _sig(getattr(b, field))
            match = 1.0 if va == vb else 0.0
            if not (_known(va) and _known(vb)):
                match = 0.0
            contribution = weight * match
            total += contribution
            dims.append({
                "field": field,
                "weight": weight,
                "a": va,
                "b": vb,
                "match": int(match),
            })

        # Hard rule (PRD section 14): differing barrier state where either
        # side is a non-failure state blocks grouping entirely.
        sa, sb = getattr(a, STATE_FIELD), getattr(b, STATE_FIELD)
        ba, bb = getattr(a, BARRIER_FIELD), getattr(b, BARRIER_FIELD)
        if (
            _known(sa) and _known(sb) and sa != sb
            and ("verified" in (sa, sb))
        ):
            total = 0.0
            dims.append({
                "field": "hard_rule",
                "weight": -1.0,
                "a": sa,
                "b": sb,
                "match": 0,
                "note": "verified vs non-verified barrier state blocks grouping",
            })

        similarity = total / max_w if max_w else 0.0
        return {
            "similarity": round(similarity, 6),
            "details": dims,
        }


def blend_with_embedding(structural: float, cosine: float | None,
                         blend: float = 0.05) -> float:
    """Embeddings may support, never dominate, structural similarity."""
    if cosine is None:
        return structural
    cosine = max(0.0, min(1.0, float(cosine)))
    return round(structural * (1 - blend) + cosine * blend, 6)


def attention_for(score: float) -> float:
    """Transform a similarity score into a monotonic 0-100 attention value."""
    if score <= 0:
        return 0.0
    return round(100.0 * math.tanh(score * 3.0), 2)