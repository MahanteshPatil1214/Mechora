"""Evidence grounding layer.

Every extracted attribute is traced back to a span in the original narrative.
If a value cannot be grounded, it is left as ``unknown`` / ``needs_review``
rather than invented (PRD FR-03 / Risk 3 mitigation).
"""

from __future__ import annotations

from app.models.safety_event import EVIDENCE_STATUS, Evidence
from app.services.negation.engine import split_sentences
from app.services.normalization.ontology import normalize_text


class EvidenceGrounder:
    """Finds grounded spans for canonical attributes in a narrative."""

    def ground_span(self, narrative: str, phrase: str) -> Evidence:
        """Ground an explicit matched phrase (may be empty)."""
        if not phrase:
            return Evidence(span="", sentence_index=-1, status="unknown")
        sentences = split_sentences(narrative)
        norm_target = normalize_text(phrase)
        for idx, sent in enumerate(sentences):
            norm = normalize_text(sent)
            if norm_target and norm_target in f" {norm} ":
                return Evidence(
                    span=sent, sentence_index=idx, status="grounded"
                )
        # fall back to token-level containment of the matched phrase
        tokens = norm_target.split()
        if tokens:
            for idx, sent in enumerate(sentences):
                norm = f" {normalize_text(sent)} "
                if all(f" {t} " in norm for t in tokens):
                    return Evidence(
                        span=sent, sentence_index=idx, status="grounded"
                    )
        return Evidence(span="", sentence_index=-1, status="needs_review")

    def ground_sentence_matching(self, narrative: str,
                                 keywords: list[str]) -> Evidence:
        """Ground the first sentence containing any keyword."""
        sentences = split_sentences(narrative)
        for idx, sent in enumerate(sentences):
            norm = normalize_text(sent)
            if any(k and k in norm for k in keywords):
                return Evidence(span=sent, sentence_index=idx, status="grounded")
        return Evidence(span="", sentence_index=-1, status="unknown")


def evidence_status_for(value: str | None) -> EVIDENCE_STATUS:
    if not value or value in ("unknown", "needs_review", "none_identified"):
        return "unknown"
    return "grounded"