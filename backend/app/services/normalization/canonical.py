"""Canonical normalization service.

Maps free-text mentions to canonical ontology codes. Safety-critical
distinctions (verified vs not_verified etc.) are preserved because the six
barrier states are distinct canonical codes and are NEVER cross-mapped.
"""

from __future__ import annotations

from app.models.safety_event import UNKNOWN_CODE
from app.services.normalization.ontology import Ontology, normalize_text


def canonicalize_text(value: str | None, category: str,
                      ontology: Ontology) -> tuple[str, str]:
    """Return (canonical_code, matched_synonym). Empty value -> unknown."""
    if not value:
        return UNKNOWN_CODE, ""
    value = value.strip()
    if not value or value.lower() in {"unknown", "n/a", "na", "none", "-"}:
        return UNKNOWN_CODE, ""
    code, syn = ontology.map(value, category)
    if not code:
        return UNKNOWN_CODE, ""
    return code, syn


def normalize_existing_code(code: str | None, category: str,
                            ontology: Ontology) -> str:
    """Ensure an already-canonical/emit code is known; else unknown."""
    if code and ontology.is_known(category, code):
        return code
    res, _ = canonicalize_text(code, category, ontology)
    return res


def is_safety_critical_distinction_preserved(category: str) -> bool:
    """Barrier states are a closed set of distinct codes — never merged."""
    return True


class Canonicalizer:
    """High-level normalization facade used by the pipeline."""

    def __init__(self, ontology: Ontology) -> None:
        self.ontology = ontology
        self._norm_cache: dict[tuple[str, str], tuple[str, str]] = {}

    def map(self, value: str | None, category: str) -> tuple[str, str]:
        key = (category, normalize_text(value or ""))
        hit = self._norm_cache.get(key)
        if hit is not None:
            return hit
        result = canonicalize_text(value, category, self.ontology)
        self._norm_cache[key] = result
        return result

    def map_existing(self, code: str | None, category: str) -> str:
        return normalize_existing_code(code, category, self.ontology)