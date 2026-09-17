"""Deterministic negation / barrier-state engine.

This is a critical MVP capability (PRD section 7C / FR-04). The engine decides
barrier state from clause-level cues so that ``verified`` and ``not_verified``
are never confused, and it is fully unit-testable. The LLM proposes a state;
this engine is authoritative.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.safety_event import BARRIER_STATE_CODES
from app.services.normalization.ontology import Ontology, normalize_text


@dataclass
class BarrierStateResult:
    state: str = "unknown"
    evidence_span: str = ""
    sentence_index: int = -1
    cues_matched: list[str] = field(default_factory=list)
    confidence: float = 0.0
    mechanism: str = ""


class NegationEngine:
    """Sentence/clause-level barrier-state classification."""

    def __init__(self, ontology: Ontology) -> None:
        self.cues = ontology.negation_cues().get("states", {})
        self.context_terms = ontology.negation_cues().get("barrier_context_terms", {})
        # Internal cue-group keys (e.g. "negated") map onto canonical
        # barrier-state codes (e.g. "not_verified").
        self._canonical = {"negated": "not_verified"}
        self._order: list[str] = sorted(
            self.cues, key=lambda s: self.cues[s].get("priority", 0), reverse=True
        )

    # ------------------------------------------------------------------ API

    def classify_barrier(self, barrier: str, narrative: str) -> BarrierStateResult:
        """Classify the state of a canonical barrier within a narrative."""
        sentences = split_sentences(narrative)
        terms = list(self.context_terms.get(barrier, []))
        if not terms and barrier and barrier != "unknown":
            terms = [barrier.replace("_", " ")]

        relevant: list[tuple[int, str]] = []
        for idx, sent in enumerate(sentences):
            norm = normalize_text(sent)
            if barrier_mentioned(barrier, norm, terms):
                relevant.append((idx, norm))

        if not relevant:
            return BarrierStateResult(state="unknown", mechanism="no_barrier_mention")

        best: BarrierStateResult | None = None
        best_priority = -1
        for idx, norm in relevant:
            state, span, cues = self._classify_norm(norm)
            priority = self._priority_for(state)
            if priority > best_priority:
                best_priority = priority
                best = BarrierStateResult(
                    state=state,
                    evidence_span=span,
                    sentence_index=idx,
                    cues_matched=cues,
                    confidence=self._confidence_for(state),
                    mechanism="negation_engine",
                )
        if best is None:
            return BarrierStateResult(state="unknown", mechanism="no_clue")

        # Ambiguity guard: if the top result across sentences is 'verified' or
        # 'unknown' but another barrier-related sentence clearly shows a
        # failure state, prefer the failure state (conservative, HSE-focused).
        if best.state in ("verified", "unknown"):
            classified = [
                (idx, norm, self._classify_norm(norm))
                for idx, norm in relevant
            ]
            failures = [
                (idx, state, span, cues)
                for idx, _norm, (state, span, cues) in classified
                if state in ("failed", "absent", "partially_effective", "not_verified")
            ]
            if failures:
                fail_priority = max(
                    (self._priority_for(s) for _, s, _, _ in failures), default=-1
                )
                best_priority = self._priority_for(best.state)
                if fail_priority > best_priority:
                    idx, fstate, fspan, fcues = max(
                        failures,
                        key=lambda f: self._priority_for(f[1]),
                    )
                    return BarrierStateResult(
                        state=fstate,
                        evidence_span=fspan,
                        sentence_index=idx,
                        cues_matched=fcues,
                        confidence=self._confidence_for(fstate),
                        mechanism="negation_engine",
                    )

        # Protective-device rule: for machinery_guarding, a device that
        # "tripped" or "operated" in response to an overload is working as
        # designed (verified), not failed.
        if best and barrier == "machinery_guarding" and best.state == "failed":
            sent_norm = normalize_text(sentences[best.sentence_index])
            if any(k in sent_norm for k in ("relay", "breaker", "device")):
                best = BarrierStateResult(
                    state="verified",
                    evidence_span=best.evidence_span,
                    sentence_index=best.sentence_index,
                    cues_matched=best.cues_matched,
                    confidence=0.91,
                    mechanism="protective_device_heuristic",
                )
        return best

    def classify_sentence(self, sentence: str) -> BarrierStateResult:
        """Classify an arbitrary sentence (used by unit tests & critical suite)."""
        norm = normalize_text(sentence)
        state, span, cues = self._classify_norm(norm)
        return BarrierStateResult(
            state=state,
            evidence_span=span,
            sentence_index=0,
            cues_matched=cues,
            confidence=self._confidence_for(state),
            mechanism="negation_engine",
        )

    # ------------------------------------------------------------- internals

    def _classify_norm(self, norm: str) -> tuple[str, str, list[str]]:
        """Return (canonical_state, matched_span, matched_cues), priority order."""
        for group in self._order:
            matches = [c for c in self.cues[group]["cues"] if c in norm]
            if group == "absent":
                # "pressure was absent" describes the energy, not the barrier.
                if "absent" in matches and " pressure " in f" {norm} ":
                    matches = [c for c in matches if c != "absent"]
            if matches:
                state = self._canonical.get(group, group)
                span = max(matches, key=len)
                return state, span, matches
        return "unknown", "", []

    def _priority_for(self, state: str) -> int:
        if state in self.cues:
            return self.cues[state].get("priority", 0)
        group = next((k for k, v in self._canonical.items() if v == state), state)
        return self.cues.get(group, {}).get("priority", 0)

    def _confidence_for(self, state: str) -> float:
        table = {
            "verified": 0.92,
            "not_verified": 0.95,
            "failed": 0.93,
            "absent": 0.9,
            "partially_effective": 0.88,
            "unknown": 0.15,
        }
        return table.get(state, 0.1)

    @staticmethod
    def has_negation(sentence: str) -> bool:
        norm = normalize_text(sentence)
        negation_cues = (
            " not ", " no ", " without ", " never ", " failed to ",
            " unverified ", " unconfirmed ", " before ", " prior to ",
        )
        padded = f" {norm} "
        return any(c in padded for c in negation_cues)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def barrier_mentioned(barrier: str, norm_sentence: str, context_terms: list[str]) -> bool:
    if not barrier or barrier == "unknown":
        return False
    if context_terms:
        return any(t in norm_sentence for t in context_terms)
    label = barrier.replace("_", " ")
    return label in norm_sentence