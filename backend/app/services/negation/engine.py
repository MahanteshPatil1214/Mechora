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


# Module-level regexes for the "negated outcome" family. A negated outcome
# ("no gas was released", "nothing leaked", "without any release of gas") is a
# NON-event: the hazard did not materialize. It must never be treated as a
# barrier failure, and it must never set exposure/extraction values.
# NOTE: normalize_text replaces clause punctuation with whitespace, so these
# patterns require a tight auxiliary-verb structure instead of a loose filler
# window that could cross clauses.
_RE_NEGATED_OUTCOME = re.compile(
    r"\b(?:no|nothing|never|none)\s+(?:[\w-]+\s+){0,2}"
    r"(?:was|were|have|has|had|got)\s+"
    r"(?:released|releasing|leaked|leaking|escaped|escaping|discharged|"
    r"discharging|spilled|spilling|vented|venting|blown|blew)\b"
)
_RE_NEGATED_OUTCOME_NOUN = re.compile(
    r"\b(?:no|nothing|without|never|none)\s+(?:any\s+)?"
    r"(?:release|releases|leak|leaks|leakage|leakages|escape|escapes|"
    r"discharge|discharges|spill|spills)\b"
)
_RE_NEGATED_OUTCOME_NOAUX = re.compile(
    r"\b(?:no|nothing|never|none)\s+(?:[\w-]+\s+)?"
    r"(?:released|releasing|leaked|leaking|escaped|escaping|discharged|"
    r"discharging|spilled|spilling|vented|venting|blown|blew)\b"
)
# All three non-event spellings, checked in order by the helper and by the
# extraction layer so exposure spans are only negated when the negation
# matches in the span's own region.
_NEGATED_OUTCOME_REGEXES = (
    _RE_NEGATED_OUTCOME,
    _RE_NEGATED_OUTCOME_NOUN,
    _RE_NEGATED_OUTCOME_NOAUX,
)

# Negated HARM / consequence statements: "no injury occurred", "no medical
# treatment was required", "no injuries were sustained", "nobody was hurt".
# Like a negated outcome, a negated consequence is a NON-consequence: it must
# NEVER be converted back into a positive actual-consequence value ("no
# medical treatment" is not evidence that medical treatment happened).
_RE_NEGATED_CONSEQUENCE = re.compile(
    r"\b(?:no|nothing|never|without|not)\s+(?:[\w-]+\s+){0,4}"
    r"(?:injur\w*|accident\w*|harm\w*|damag\w*|fatalit\w*|death\w*|"
    r"treatment\w*|first\s+aid\w*|hospital\w*|burn\w*|cut\w*|event\w*)\b"
)
_RE_NEGATED_CONSEQUENCE_NOUN = re.compile(
    r"\b(?:no|nothing|never|without)\s+(?:[\w-]+\s+){0,4}"
    r"(?:injury|injuries|harm|damage|fatality|fatalities|death|" 
    r"medical\s+treatment|first\s+aid|hospitalisation|hospitalization|burn|cut)\b"
)
_NEGATED_CONSEQUENCE_REGEXES = (
    _RE_NEGATED_CONSEQUENCE,
    _RE_NEGATED_CONSEQUENCE_NOUN,
)

# Explicit POSITIVE verification of a control/barrier: "was/were verified",
# "was confirmed", "has been checked", "fully verified", "was applied". Only
# matches when the verification verb is un-negated ("was NOT verified",
# "was NEVER confirmed" do not match, because the negator sits between the
# auxiliary and the verb). Used so an explicit positive verification outranks
# an unrelated 'before/prior to' clause.
_POSITIVE_VERIFIED_RE = re.compile(
    r"\b(?:was|were|is|are|has\s+been|had\s+been|have\s+been)\s+"
    r"(?:fully\s+|strictly\s+|physically\s+|independently\s+)?"
    r"(?:proven|proved|verified|confirmed|checked|established|tested|approved|"
    r"completed|issued|applied|isolated|locked|depressuriz\w+|signed|posted)\w*"
)

# Work/action verb occurring BEFORE a 'before/prior to' clause: marks the
# order-violation construction ("opened the drain before the line was proven
# depressurized" -> verification came too late -> not_verified). Absent when
# the sentence is FRONTED with the 'before' clause ("Before opening the joint,
# isolation was verified" -> positive statement -> verified).
_ACTION_BEFORE_RE = re.compile(
    r"\b(?:open(?:ed|ing)?|start\w*|began|begun|begins?|beginning|remove\w*|"
    r"disconnect\w*|unbolt\w*|loosen\w*|loosening|break\w*|dismantl\w*|"
    r"work(?:ed|ing)?|commenc\w*|enter\w*|proceed\w*|attempt\w*)\b"
    r".*?\b(?:before|prior\s+to)\b"
)


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

    def _negated_outcome_match(self, norm: str) -> "re.Match[str] | None":
        """Return the first negated-outcome match (aux, noun or no-aux form).

        Shared by barrier-state classification and the extraction layer so a
        non-event ("no gas was released") is NEVER converted into a positive
        exposure/energy attribute.
        """
        for _rx in _NEGATED_OUTCOME_REGEXES:
            m = _rx.search(norm)
            if m:
                return m
        return None

    def negates_outcome(self, norm: str) -> bool:
        """True when the normalized clause describes a NON-event (no release /
        no leak / nothing escaped). Used to keep exposure extractions honest."""
        return self._negated_outcome_match(norm) is not None

    def negates_outcome_span(self, norm: str, span_norm: str) -> bool:
        """True when a negated-outcome non-event overlaps the span's location.

        Region-scoped so that in a clause-fused sentence ("gas was heard
        leaking from a flange; no gas was released") a genuine positive
        'leaking' span is NOT discarded just because a negated release clause
        appears later in the same sentence."""
        if not span_norm or not norm:
            return False
        for _rx in _NEGATED_OUTCOME_REGEXES:
            for m in _rx.finditer(norm):
                start, end = m.span()
                pos = norm.find(span_norm)
                while pos != -1:
                    if pos < end and (pos + len(span_norm)) > start:
                        return True
                    pos = norm.find(span_norm, pos + 1)
        return False

    def negates_consequence_span(self, norm: str, span_norm: str) -> bool:
        """True when a negated-harm statement overlaps a consequence span.

        Region-scoped (like :meth:`negates_outcome_span`) so "No injury
        occurred and no medical treatment was required." marks BOTH 'injury'
        and 'medical treatment' as non-consequences while a genuine "a worker
        sustained a minor cut" sentence that never states a negation keeps the
        positive span."""
        if not span_norm or not norm:
            return False
        for _rx in _NEGATED_CONSEQUENCE_REGEXES:
            for m in _rx.finditer(norm):
                start, end = m.span()
                pos = norm.find(span_norm)
                while pos != -1:
                    if pos < end and (pos + len(span_norm)) > start:
                        return True
                    pos = norm.find(span_norm, pos + 1)
        return False

    _FAILURE_STATES = {"not_verified", "failed", "absent", "partially_effective"}

    # Substantive control/verification terms: a 'negated'-group cue only
    # counts as an explicit barrier-failure assertion when it references one
    # of these (e.g. "was not verified", "not confirmed", "permit not
    # issued", "skipped"). Bare particles ("no", "not", "never", "was not")
    # are NOT specific enough.
    _CONTROL_TERM = re.compile(
        r"\b(?:verif\w*|confirm\w*|check\w*|test\w*|establi\w*|prove[n]?\w*|complet\w*|"
        r"perform\w*|done|issu\w*|approval|approv\w*|permit|isolat\w*|"
        r"depressur\w*|zero\s+energy|zero\s+pressure|skip\w*|omit\w*|ensur\w*|"
        r"lock\w*|guard\w*)\b"
    )

    def _failure_cue_match(self,
                           norm: str) -> tuple[str, str, list[str]] | None:
        """Highest-priority explicit failure cue in a sentence, or None.

        Used to keep a negated-outcome clause ("no gas was released") from
        overriding a real control failure stated in the same sentence. Only
        DIRECT failure groups plus substantive control-verb negations
        ("was not verified", "not confirmed", "skipped") participate; the bare
        'negated' particles ("no", "not", "never") never count as an explicit
        failure assertion."""
        best: tuple[str, str, list[str]] | None = None
        for group in self._order:
            if group not in self._FAILURE_STATES and group != "negated":
                continue
            state = self._canonical.get(group, group)
            matches = [c for c in self.cues[group]["cues"] if c in norm]
            if group == "negated":
                matches = [c for c in matches if self._CONTROL_TERM.search(c)]
            if group == "absent" and "absent" in matches and \
                    " pressure " in f" {norm} ":
                matches = [c for c in matches if c != "absent"]
            if not matches:
                continue
            priority = self.cues[group].get("priority", 0)
            if best is None or priority >= self._priority_for(best[0]):
                best = (state, max(matches, key=len), matches)
        return best

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
        # Applicability guard: "isolation was NOT required / not needed for this
        # task" means the barrier was never applicable, not that it was skipped.
        # This is a different story than a failure (not_verified/failed), so it
        # must resolve to UNKNOWN and be held for HSE review instead of being
        # counted as a barrier-failure signal.
        not_required = re.search(
            r"\b(?:is|was|were|has\s+been|being)?\s*not\s+"
            r"(?:required|needed|necessary)\b",
            norm,
        )
        if not_required:
            span = not_required.group(0)
            return "unknown", span, [span]

        # Negated failure pattern: "did not fail", "never failed", "did not
        # rupture", "was not skipped" etc. Indicates the barrier action was
        # actually carried out / held -> verified. "Was not skipped" means the
        # verification step was performed, so it is a positive (verified)
        # check, never a not_verified assertion.
        negated_failure = re.search(
            r"\b(?:did\s+not|didn't|had\s+not|was\s+not|were\s+not|never|no|without)\s+(?:fail|failed|failure|rupture|ruptured|leak|leakage|burst|skipped|omitted|omit|skip)\b",
            norm,
        )
        if negated_failure:
            span = negated_failure.group(0)
            return "verified", span, [span]

        # Inability clause: "could not be confirmed / verified / established"
        # leaves the barrier state indeterminate. This is NOT a definite
        # NOT_VERIFIED / FAILED assertion, so it resolves to UNKNOWN and is
        # held for NEEDS_REVIEW by the pipeline instead of being guessed.
        inability = re.search(
            r"\b(?:could\s+not|couldn't)\s+be\s+"
            r"(?:confirmed|verified|established|proven|proved|determined)\w*",
            norm,
        )
        if inability:
            span = inability.group(0)
            return "unknown", span, [span]

        # Negated outcome: "no gas was released / no leak occurred / nothing was
        # released / without any release" describes a NON-event (the hazard did
        # not materialize), not a barrier failure. The bare 'no'/'without'/'never'
        # cues must not reverse such a positive outcome into not_verified.
        # NOTE: normalize_text replaces clause punctuation with whitespace, so
        # these patterns require a tight auxiliary-verb structure ('no <x> was
        # released') instead of a loose filler window that could cross clauses.
        negated_outcome = self._negated_outcome_match(norm)
        if negated_outcome:
            # A negated outcome must NOT blind an explicit barrier-failure
            # assertion in the SAME sentence ("isolation was not verified and
            # no gas was released" is still NOT_VERIFIED for the isolation).
            fail = self._failure_cue_match(norm)
            if fail:
                return fail
            span = negated_outcome.group(0)
            return "verified", span, [span]

        temporal_match = re.search(
            r"\b(?:before|prior\s+to)\b.*?\b(proven|verified|confirmed|depressuriz|isolated|checked|tested|verification|confirmation)\w*",
            norm,
        )
        if temporal_match:
            # Precedence: an explicit un-negated positive verification in the
            # sentence outranks an unrelated 'before/prior to' clause, UNLESS
            # the order-violation construction holds (a work/action verb
            # precedes the 'before' clause: "opened the drain before the line
            # was proven depressurized"). "Before opening the joint, isolation
            # was verified" is a POSITIVE statement -> verified; only the
            # action-first disorder pattern is not_verified.
            positive = _POSITIVE_VERIFIED_RE.search(norm)
            action_before = _ACTION_BEFORE_RE.search(norm)
            if positive and not action_before:
                fail = self._failure_cue_match(norm)
                if fail:
                    return fail
                span = positive.group(0)
                return "verified", span, [span]
            span = temporal_match.group(0)
            return "not_verified", span, [span]

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


def sentence_containing(narrative: str, span: str) -> str:
    """Return the full sentence that contains ``span`` (verbatim), or ``span``
    when no containing sentence is found.

    Used so barrier-STATE evidence carries the whole causal sentence
    ("the technician loosened the bonnet studs before cracking the bleeder
    needle valve to confirm depressurization.") while the barrier VALUE's
    evidence stays the narrower verification phrase ("before cracking the
    bleeder needle valve to confirm depressurization")."""
    if not span or not narrative:
        return span or ""
    span_norm = normalize_text(span)
    for sent in split_sentences(narrative):
        if span_norm and span_norm in normalize_text(sent):
            return sent
    return span


def barrier_mentioned(barrier: str, norm_sentence: str, context_terms: list[str]) -> bool:
    if not barrier or barrier == "unknown":
        return False
    if context_terms:
        return any(t in norm_sentence for t in context_terms)
    label = barrier.replace("_", " ")
    return label in norm_sentence