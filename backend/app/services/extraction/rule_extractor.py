"""Deterministic (rule-based) extraction service.

Offline fallback that mirrors the strict LLM extraction schema. Used when no
Gemini key is available so the full pipeline, tests and evaluation run
reproducibly. It grounds every field in narrative text and never invents
values: unmatched fields become ``unknown``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.models.safety_event import (
    LLMExtraction,
    BARRIER_FAILURE_STATES,
    UNKNOWN_CODE,
)
from app.services.evidence.evidence import EvidenceGrounder
from app.services.negation.engine import (
    NegationEngine,
    sentence_containing,
    split_sentences,
)
from app.services.normalization.canonical import Canonicalizer
from app.services.normalization.ontology import Ontology, normalize_text


@dataclass
class ExtractionOutput:
    extraction: LLMExtraction
    matched: dict[str, str] = field(default_factory=dict)
    multi_energies: list[dict[str, Any]] = field(default_factory=list)
    multi_barriers: list[dict[str, Any]] = field(default_factory=list)
    provider: str = "rules"


def inferred_potential_consequence(
    energy: str,
    exposure: str,
    barrier_state: str,
    ontology: Ontology,
) -> str:
    """Rule-based potential consequence. Never invented: an unmitigated SIF
    potential is only asserted when real hazard/exposure evidence exists.

    ``barrier_state == verified`` extinguishes the potential (controls intact).
    Unknown energy AND unknown exposure produce ``unknown``: there is no
    grounded hazard, so no consequence is asserted.
    """
    if barrier_state == "verified":
        return UNKNOWN_CODE

    has_energy = bool(energy and energy != UNKNOWN_CODE)
    has_exposure = bool(exposure and exposure != UNKNOWN_CODE)
    if not has_energy and not has_exposure:
        return UNKNOWN_CODE

    e_rank = ontology.energy_rank(energy) if has_energy else 0
    ex_rank = ontology.exposure_rank(exposure) if has_exposure else 0

    if e_rank >= 4 or ex_rank >= 4:
        return "serious_injury_or_fatality"
    if e_rank >= 2 or ex_rank >= 2:
        return "injury"
    if e_rank >= 1 or ex_rank >= 1:
        return "minor_injury"
    return UNKNOWN_CODE


# Energy -> required barrier inference when no barrier word is mentioned.
ENERGY_DEFAULT_BARRIER = {
    "pressurized_gas": "energy_isolation",
    "pressurized_liquid": "energy_isolation",
    "electrical_energy": "energy_isolation",
    "stored_mechanical_energy": "energy_isolation",
    "thermal_energy": "energy_isolation",
    "flammable_atmosphere": "hot_work_controls",
    "chemical_exposure": "chemical_handling_controls",
    "gravity": "fall_protection",
    "moving_equipment": "machinery_guarding",
}

# Tie-break markers for primary-energy selection. When several energies share
# the same severity rank, a span that names the actual SUBSTANCE (crude,
# slurry, gas, liquid, hydrocarbon...) is the real hazard and must beat generic
# pressure-state wording ("depressurization", "zero pressure") that merely
# describes a barrier check. A barrier-verification word is evidence about the
# isolation, not about the hazard being contained.
_SUBSTANCE_MARKERS = (
    "gas", "liquid", "slurry", "crude", "oil", "water", "vapour", "vapor",
    "fluid", "hydrocarbon", "acid", "caustic", "h2s", "flammable", "solvent",
    "chemical",
)
_GENERIC_PRESSURE_MARKERS = (
    "depressuriz", "depressuris", "zero pressure", "no pressure",
    "pressure absent", "pressure present", "pressure system", "pressuris",
    "pressure", "pressurized system", "pressurised system",
)

# Energy evidence is the noun phrase naming the CONTAINED HAZARD, so the
# matched substance word is expanded to its full descriptive phrase ("warm
# crude and sour water" -> "trapped slurry of warm crude and sour water") but
# never across an action/release verb ("sprayed onto the drip pan...").
_HAZARD_CONTINUE_WORDS = {
    "a", "an", "the", "of", "and", "or", "in", "on", "at", "from", "within",
    "with", "trapped", "contained", "stored", "captured", "residual",
    "remaining", "retained", "pressurized", "pressurised", "hazardous",
    "flammable", "combustible", "toxic", "corrosive", "hot", "warm", "cold",
    "wet", "stagnant", "slurry", "crude", "oil", "water", "sour", "acid",
    "gas", "vapour", "vapor", "hydrocarbon", "liquid", "condensate", "sludge",
    "mud",
}
_WORD = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")

# Explicit pre-job PHASE constructions name the preparation/verification step
# itself ("...without prior zero-energy verification", "before work started",
# "Pre-job: ..."), regardless of which activity the job belongs to. They
# therefore outrank the activity-implied maintenance phase, which merely says a
# job was in progress. Cues are compared against normalize_text() output, so
# hyphenated spellings ("pre-job") appear here in normalised "pre job" form.
_EXPLICIT_PRE_JOB_CUES = (
    "without prior",
    "prior to",
    "before work started",
    "before starting work",
    "pre job",
    "preparation for work",
)


class RuleBasedExtractor:
    """Extracts structured safety attributes with deterministic rules."""

    def __init__(
        self,
        ontology: Ontology,
        canonicalizer: Canonicalizer,
        negation: NegationEngine,
        grounder: EvidenceGrounder,
    ) -> None:
        self.ontology = ontology
        self.canonicalizer = canonicalizer
        self.negation = negation
        self.grounder = grounder

    # ------------------------------------------------------------------ main

    def extract(self, report_id: str, narrative: str) -> ExtractionOutput:
        matched: dict[str, str] = {}
        norm = normalize_text(narrative)

        activity, a_span = self.canonicalizer.map(narrative, "activity")
        matched["activity"] = self._extract_verbatim_span(narrative, a_span) if a_span else ""

        task_phase, t_span = self.canonicalizer.map(narrative, "task_phase")
        matched["task_phase"] = self._extract_verbatim_span(narrative, t_span) if t_span else ""

        energies, en_spans = self._detect_category(narrative, "energy")
        if not energies and activity == "hot_work":
            energies = ["flammable_atmosphere"]
            en_spans = {"flammable_atmosphere": "hot work"}
        primary_energy = self._pick_primary(energies, en_spans, "energy")
        matched["energy"] = self._expand_hazard_span(
            narrative,
            self._extract_verbatim_span(
                narrative, en_spans.get(primary_energy, "")
            ) if primary_energy in en_spans else "",
        )
        energy_codes = [e for e in energies]

        # Task-phase inference: a known activity always implies an active job
        # ("maintenance"); unknown activity uses pre/post job temporal cues
        # or verification-condition patterns (the classic negation-sentence
        # forms like "X was not confirmed").  Phrases that name specific
        # activities ("cleaning", "testing") are suppressed when activity is
        # unknown so the pre/post heuristics can take over.
        # An EXPLICIT pre-job phase construction wins over BOTH the
        # activity-implied "maintenance" phase and any phase the ontology
        # matched incidentally (e.g. "maintenance" elsewhere in the sentence):
        # the observation is about the preparation/verification step.
        # Evidence (NOT canonical value) stays the exact verbatim source span.
        explicit_pre = any(t in norm for t in _EXPLICIT_PRE_JOB_CUES)
        if explicit_pre:
            task_phase = "pre_job"
            matched["task_phase"] = self._verbatim_first(
                narrative, _EXPLICIT_PRE_JOB_CUES
            )
        elif activity and activity != UNKNOWN_CODE:
            task_phase = "maintenance"
            mc = self.ontology.concept("task_phase", "maintenance")
            matched["task_phase"] = self._verbatim_first(
                narrative, list(mc.synonyms) if mc else ["maintenance"]
            )
        elif task_phase == UNKNOWN_CODE or task_phase in (
                "testing", "cleaning", "repair", "inspection", "operation"):
            pre_words = (
                "before work", "before the job", "before start",
                "prior to work", "before entry", "before work started",
                "prior to the job", "before work commenced",
            )
            verification_words = (
                "confirmed", "verified", "checked", "tested",
                "lockout", "depressuriz", "permit", "isolated",
                "issued", "proved", "confirm", "verify", "check",
                "test", "verification", "checking", "carried out",
            )
            post_words = (
                "after work", "after the job", "when the job was completed",
                "when work was completed", "after completion",
            )
            if any(t in norm for t in pre_words) or any(
                t in norm for t in verification_words
            ):
                task_phase = "pre_job"
                matched["task_phase"] = self._verbatim_first(narrative, pre_words)
            elif any(t in norm for t in post_words):
                task_phase = "post_job"
                matched["task_phase"] = self._verbatim_first(narrative, post_words)

        exposure, ex_span = self._exposure_for(narrative, norm)
        ex_evidence = self._extract_verbatim_span(narrative, ex_span) if ex_span else ""
        matched["exposure"] = self._exposure_event_phrase(narrative, ex_evidence)

        barrier, bar_span, inferred = self._detect_barrier(
            narrative, norm, energy_codes
        )
        matched["barrier"] = self._extract_verbatim_span(narrative, bar_span) if bar_span else ""

# Barrier state: negation engine is authoritative.
        state_result = self.negation.classify_barrier(barrier, narrative)
        barrier_state = state_result.state
        state_span = self._extract_verbatim_span(
            narrative, state_result.evidence_span
        ) if state_result.evidence_span else ""
        # Barrier evidence vs barrier-STATE evidence stay distinct:
        #   barrier evidence = the most specific phrase that NAMES the control
        #   (the verification phrase when it verbatim-wraps the bare barrier
        #   mention, e.g. "before cracking the bleeder needle valve to confirm
        #   depressurization" > bare "depressurization");
        #   barrier_state evidence = the FULL causal sentence carrying that
        #   verification phrase ("the mechanical technician loosened the
        #   bonnet studs before cracking the bleeder needle valve to confirm
        #   depressurization."). The two are never conflated, and the barrier
        #   VALUE (e.g. energy_isolation) is never presented as evidence.
        bar_evidence = matched["barrier"]
        if (
            bar_evidence
            and state_span
            and len(state_span) > len(bar_evidence)
            and bar_evidence.lower() in state_span.lower()
        ):
            bar_evidence = state_span
        elif (not bar_evidence) and state_span:
            bar_evidence = state_span
        matched["barrier"] = self._barrier_evidence_phrase(narrative, bar_evidence)
        matched["barrier_state"] = (
            sentence_containing(narrative, state_span) if state_span else ""
        )
        state_confidence = state_result.confidence

        consequence, c_span = self._detect_actual_consequence(narrative)
        matched["actual_consequence"] = self._extract_verbatim_span(narrative, c_span) if c_span else ""

        location, l_span = self.canonicalizer.map(narrative, "location")
        matched["location"] = self._extract_verbatim_span(narrative, l_span) if l_span else ""

        unsafe_action = self._unsafe_action(
            barrier, barrier_state, state_result.evidence_span, energy_codes
        )
        unsafe_condition = self._unsafe_condition(energy_codes, barrier_state)

        potential = self._potential_consequence(
            primary_energy, exposure, barrier_state
        )
        # NOTE: no `matched["potential_consequence"]` evidence is attached here.
        # The rule-inferred potential consequence is NOT narrative evidence; it
        # is model inference. Evidence is only attached downstream when the
        # text explicitly states the exact same consequence (see pipeline).

        life_saving_rules = self._lsr_from(barrier, primary_energy,
                                            exposure, barrier_state)

        evidence = self._collect_evidence(narrative, matched, barrier_state)

        confidence = self._overall_confidence(
            activity, task_phase, primary_energy, barrier,
            barrier_state, exposure, location, consequence
        )

        extraction = LLMExtraction(
            activity=activity,
            task_phase=task_phase,
            hazard=self.ontology.label("energy", primary_energy) or "unknown",
            energy=primary_energy,
            unsafe_action=unsafe_action,
            unsafe_condition=unsafe_condition,
            barrier=barrier,
            barrier_state=barrier_state,
            exposure=exposure,
            actual_consequence=consequence,
            potential_consequence=potential,
            location=location,
            life_saving_rules=life_saving_rules,
            evidence=evidence,
            confidence=max(round(confidence, 4), state_confidence * 0.9),
        )

        return ExtractionOutput(
            extraction=extraction,
            matched=matched,
            multi_energies=[{"code": c, "span": en_spans[c]} for c in energy_codes],
            multi_barriers=[{"code": c, "span": s} for c, s in self._barrier_map],
            provider="rules",
        )

    # ------------------------------------------------------------ internals

    def _detect_category(self, narrative: str, category: str):
        """Detect multiple concepts of a category -> (codes, span_by_code)."""
        spans: dict[str, str] = {}
        codes: list[str] = []
        for concept in self.ontology.concepts(category):
            c_code, c_span = self._best_synonym_match(narrative, category,
                                                      concept.code)
            if c_code:
                codes.append(c_code)
                spans[c_code] = c_span
        return codes, spans

    def _expand_hazard_span(self, narrative: str, span: str) -> str:
        """Expand a matched hazard word to its full descriptive phrase.

        Example: the energy evidence "sour water" becomes "trapped slurry of
        warm crude and sour water" by absorbing the descriptive noun phrase
        that precedes it, but the expansion is capped by a curated continuation
        lexicon so it never crosses an action/release verb ("sprayed onto the
        drip pan..."). The expanded span is always verbatim in the narrative.
        """
        if not span or not narrative:
            return span
        target = re.escape(span)
        for sent in split_sentences(narrative):
            m = re.search(r"(?<!\w)" + target + r"(?!\w)", sent, re.IGNORECASE)
            if not m:
                continue
            before = sent[: m.start()]
            after = sent[m.end() :]
            words_left = [(w.group(0), w.start()) for w in _WORD.finditer(before)]
            words_right = [(w.group(0), w.start()) for w in _WORD.finditer(after)]
            start = m.start()
            for i in range(len(words_left) - 1, -1, -1):
                if normalize_text(words_left[i][0]) in _HAZARD_CONTINUE_WORDS:
                    start = words_left[i][1]
                else:
                    break
            keep_end = m.end()
            for w, pos in words_right:
                if normalize_text(w) in _HAZARD_CONTINUE_WORDS:
                    keep_end = pos + len(w)
                else:
                    break
            expanded = sent[start:keep_end]
            if len(expanded) > len(span):
                return expanded
        return span

    def _exposure_event_phrase(self, narrative: str, span: str) -> str:
        """Lift exposure evidence from the bare release verb to the full
        describing sentence. ``"sprayed onto"`` alone does not tell the
        reviewer WHAT was released; the full sentence ("A trapped slurry of
        warm crude and sour water sprayed onto the drip pan...") carries the
        hazard->release->exposure chain. Always verbatim; falls back to the
        bare span when no containing sentence is found.
        """
        if not span or not narrative:
            return span
        target = re.escape(span)
        for sent in split_sentences(narrative):
            if re.search(r"(?<!\w)" + target + r"(?!\w)", sent, re.IGNORECASE):
                return sent
        return span

    @staticmethod
    def _extract_verbatim_span(narrative: str, phrase: str) -> str:
        """Locate the exact verbatim span in the narrative preserving casing.

        Returns the literal text found in the narrative, or ``""`` when the
        phrase is NOT present verbatim. Never falls back to a canonical or
        synonym string (evidence must be an exact quote; otherwise show
        "no direct span"). Light separators (hyphen, slash, any whitespace)
        are tolerated AND flexibly matched so a hyphenated synonym
        ("zero energy" in text) still yields its exact span even when the
        ontology spells it "zero-energy" (and vice versa). Without this, the
        chosen synonym spelling (set-order dependent) silenced the evidence.
        """
        if not phrase or not narrative:
            return ""
        tokens = [t for t in re.split(r"[\s\-/]+", phrase) if t]
        if not tokens:
            return ""
        sep = r"[\s\-/]+"
        # Trailing look-ahead instead of a hard word boundary: a phrase that
        # ends with sentence punctuation ("No injury was reported.") is still
        # matched verbatim at end-of-string or before other punctuation.
        pattern = r"\b" + sep.join(re.escape(w) for w in tokens) + r"(?!\w)"
        m = re.search(pattern, narrative, re.IGNORECASE)
        if m:
            return m.group(0)
        return ""

    @staticmethod
    def _barrier_evidence_phrase(narrative: str, span: str) -> str:
        """Widen a bare barrier span to its complete 'before/prior to' clause.

        A barrier mention that matched a short synonym ("isolation of", "zero
        energy") becomes the whole verification clause that establishes the
        control ("before confirming complete isolation of the pressurized gas
        line"), always verbatim from the narrative and never crossing a
        sentence boundary. Idempotent: a span that already IS that clause
        ("before cracking the bleeder needle valve to confirm depressurization")
        is returned unchanged, and spans without a leading 'before/prior to'
        marker fall back to the original span."""
        if not span or not narrative:
            return span or ""
        target = re.escape(span)
        for sent in split_sentences(narrative):
            m = re.search(r"(?<!\w)" + target + r"(?!\w)", sent, re.IGNORECASE)
            if not m:
                continue
            for marker in ("prior to", "before"):
                idx = sent[: m.start()].rfind(marker)
                if idx == -1:
                    continue
                phrase = sent[idx:].strip().rstrip(".!?;")
                if len(phrase) > len(span):
                    return phrase
        return span

    @staticmethod
    def _verbatim_first(narrative: str, phrases: list[str]) -> str:
        """Return the longest verbatim narrative span matching any phrase.

        Used to ground inferred task phases (e.g. 'maintenance' behind
        'Compressor maintenance...') while keeping evidence distinct from the
        canonical value. Empty when no phrase occurs verbatim."""
        best = ""
        for p in phrases:
            if not p:
                continue
            span = RuleBasedExtractor._extract_verbatim_span(narrative, p)
            if span and len(span) > len(best):
                best = span
        return best

    def _best_synonym_match(self, narrative: str, category: str,
                            code: str) -> tuple[str, str]:
        concept = self.ontology.concept(category, code)
        if not concept:
            return "", ""
        norm_narr = f" {normalize_text(narrative)} "
        best = ""
        best_len = 0
        for syn in concept.synonyms:
            ns = normalize_text(syn)
            if ns and f" {ns} " in norm_narr and len(ns) > best_len:
                best = syn
                best_len = len(ns)
        if not best:
            return "", ""
        verbatim = self._extract_verbatim_span(narrative, best)
        return (code, verbatim)

    def verbatim_span_for_code(self, narrative: str, category: str,
                               code: str) -> str:
        """Deterministic verbatim span for a canonical code.

        Used to attribute EXPLICIT evidence to canonical values that arrived
        via the LLM path: the model proposes a value, but the evidence and its
        provenance are re-derived deterministically from the narrative so a
        field is only ever 'explicit' when real text supports it. Exposure is
        filtered so a negated non-event ('no gas was released') is never
        attached as evidence for a positive exposure. Barrier evidence follows
        the SAME phrase-wrapping rule used on the rules path so both providers
        attribute identical spans for the identical narrative.
        """
        if not code or code == UNKNOWN_CODE:
            return ""
        concept = self.ontology.concept(category, code)
        if not concept:
            return ""
        if category == "exposure":
            spans = self._all_synonym_spans(narrative, concept.synonyms)
            if not spans:
                return ""
            non_negated = [sp for sp in spans
                           if not self._exposure_negated(narrative, sp)]
            if not non_negated:
                return ""
            return max(non_negated, key=len)
        if category == "consequence":
            spans = self._all_synonym_spans(narrative, concept.synonyms)
            if not spans:
                return ""
            non_negated = [sp for sp in spans
                           if not self._consequence_negated(narrative, sp)]
            if not non_negated:
                return ""
            return max(non_negated, key=len)
        _, span = self._best_synonym_match(narrative, category, code)
        if category == "barrier" and span:
            st = self.negation.classify_barrier(code, narrative)
            st_span = self._extract_verbatim_span(
                narrative, st.evidence_span
            ) if st.evidence_span else ""
            if (st_span and len(st_span) > len(span)
                    and span.lower() in st_span.lower()):
                return self._barrier_evidence_phrase(narrative, st_span)
        return self._barrier_evidence_phrase(narrative, span)

    @staticmethod
    def _primary_energy_priority(span: str) -> int:
        norm = normalize_text(span)
        if any(m in norm for m in _SUBSTANCE_MARKERS):
            return 2
        if any(m in norm for m in _GENERIC_PRESSURE_MARKERS):
            return 0
        return 1

    def _pick_primary(self, codes: list[str], spans: dict[str, str],
                      category: str) -> str:
        if not codes:
            return UNKNOWN_CODE
        if category == "energy":
            ranked = sorted(
                codes,
                key=lambda c: (
                    self.ontology.energy_rank(c),
                    self._primary_energy_priority(spans.get(c, "")),
                    len(spans.get(c, "")),
                ),
                reverse=True,
            )
            return ranked[0]
        return codes[0]

    def _exposure_for(self, narrative: str, norm: str) -> tuple[str, str]:
        best = UNKNOWN_CODE
        best_rank = 0
        best_span = ""
        for concept in self.ontology.concepts("exposure"):
            if concept.code == UNKNOWN_CODE:
                continue
            # Consider EVERY matching synonym span, not just the longest one:
            # "gas was heard leaking from a flange; no gas was released." has a
            # positive 'leaking' span AND a negated 'gas was released' span —
            # the genuine exposure must survive while the non-event is dropped.
            spans = self._all_synonym_spans(narrative, concept.synonyms)
            if not spans:
                continue
            non_negated = [sp for sp in spans
                           if not self._exposure_negated(narrative, sp)]
            if not non_negated:
                # Every mention of this exposure is negated ("no gas was
                # released", "nothing leaked") -> a NON-event. Unknown is the
                # only honest value here.
                continue
            c_span = max(non_negated, key=len)
            rank = self.ontology.exposure_rank(concept.code)
            if rank > best_rank or (rank == best_rank and c_span):
                best = concept.code
                best_rank = rank
                best_span = c_span
        return best, best_span

    @staticmethod
    def _all_synonym_spans(narrative: str, synonyms: list[str]) -> list[str]:
        """All verbatim narrative spans matching any synonym, longest first."""
        spans: list[str] = []
        for syn in synonyms or []:
            sp = RuleBasedExtractor._extract_verbatim_span(narrative, syn)
            if sp:
                spans.append(sp)
        # Dedupe deterministically: length-descending, then alphabetical, so
        # equal-length spans don't resolve by hash-seed set order.
        return sorted(set(spans), key=lambda s: (-len(s), s))

    def _exposure_negated(self, narrative: str, span: str) -> bool:
        """True when EVERY sentence containing the exposure span negates the
        release outcome in the span's own region (e.g. "no gas was released",
        "nothing leaked"). A span also present in a positive clause is kept."""
        if not span:
            return False
        span_norm = normalize_text(span)
        if not span_norm:
            return False
        occurrences: list[bool] = []
        for sent in split_sentences(narrative):
            sent_norm = normalize_text(sent)
            if span_norm in sent_norm:
                occurrences.append(
                    self.negation.negates_outcome_span(sent_norm, span_norm)
                )
        return bool(occurrences) and all(occurrences)

    def _detect_category2(self, narrative: str, category: str):
        best = UNKNOWN_CODE
        best_span = ""
        best_len = 0
        for concept in self.ontology.concepts(category):
            c_code, c_span = self._best_synonym_match(narrative, category,
                                                      concept.code)
            if c_code and len(c_span) > best_len:
                best = c_code
                best_span = c_span
                best_len = len(c_span)
        return best, best_span

    def _consequence_negated(self, narrative: str, span: str) -> bool:
        """True when EVERY sentence containing the consequence span negates it
        ("No injury occurred", "no medical treatment was required"). A span
        also present in a positive clause keeps the positive reading."""
        if not span:
            return False
        span_norm = normalize_text(span)
        if not span_norm:
            return False
        occurrences: list[bool] = []
        for sent in split_sentences(narrative):
            if span_norm in normalize_text(sent):
                occurrences.append(
                    self.negation.negates_consequence_span(
                        normalize_text(sent), span_norm
                    )
                )
        return bool(occurrences) and all(occurrences)

    def detect_actual_consequence(self, narrative: str) -> tuple[str, str]:
        """Public (non-negation-filtered) actual-consequence detection.

        Identical semantics to :meth:`_detect_actual_consequence`; used by the
        pipeline on EVERY provider path so an "no injury occurred and no
        medical treatment was required" narrative yields ``none_identified``
        with the full negated sentence as evidence regardless of provider.
        """
        return self._detect_actual_consequence(narrative)

    def _detect_actual_consequence(self, narrative: str) -> tuple[str, str]:
        """Negation-aware ACTUAL consequence detection.

        Only NON-negated consequence statements count as a positive actual
        consequence. A negated statement ("No injury occurred and no medical
        treatment was required.") is a NON-consequence and must NEVER be read
        back as "medical treatment happened". When EVERY consequence statement
        in the narrative is negated, the honest value is ``none_identified``
        with the full negated sentence as evidence. A narrative stating no
        consequence at all stays ``unknown``.
        """
        positives: list[tuple[str, str]] = []
        negated_spans: list[str] = []
        for concept in self.ontology.concepts("consequence"):
            if concept.code == UNKNOWN_CODE:
                continue
            for span in self._all_synonym_spans(narrative, concept.synonyms):
                span_norm = normalize_text(span)
                if not span_norm:
                    continue
                occurrences: list[bool] = []
                for sent in split_sentences(narrative):
                    if span_norm in normalize_text(sent):
                        occurrences.append(
                            not self.negation.negates_consequence_span(
                                normalize_text(sent), span_norm
                            )
                        )
                if not occurrences:
                    continue
                if any(occurrences):
                    positives.append((concept.code, span))
                else:
                    negated_spans.append(span)
        if positives:
            # Longest non-negated verbatim span wins. The span itself may be a
            # negated-word synonym of none_identified ("no injury") but only
            # when it appears in POSITIVE context — those are handled above.
            return max(positives, key=lambda p: len(p[1]))
        if negated_spans:
            longest = max(negated_spans, key=len)
            for sent in split_sentences(narrative):
                if normalize_text(longest) in normalize_text(sent):
                    return "none_identified", sent
            return "none_identified", longest
        return UNKNOWN_CODE, ""

    def _detect_barrier(self, narrative: str, norm: str,
                        energy_codes: list[str]) -> tuple[str, str, bool]:
        """Detect the primary barrier.

        Priority: explicit barrier mentions (`hard`), then energy inference
        (`soft`). Returns (code, evidence_span, inferred).
        """
        norm_narr = f" {norm} "
        self._barrier_map: list[tuple[str, str]] = []
        hard: list[tuple[str, str, str]] = []  # (code, span, matching_ctx)
        for concept in self.ontology.concepts("barrier"):
            c_code, c_span = self._best_synonym_match(narrative, "barrier",
                                                      concept.code)
            if c_code:
                hard.append((c_code, c_span, ""))
                self._barrier_map.append((c_code, c_span))

        if hard:
            # Prefer a barrier whose state shows a failure (most informative).
            scored: list[tuple[int, str, str]] = []
            for code, span, _ctx in hard:
                st = self.negation.classify_barrier(code, narrative).state
                weight = 2 if st in BARRIER_FAILURE_STATES else 1
                scored.append((weight, code, span))
            # A SPECIFIC hot-work control outranks the generic work-permit
            # barrier when a narrative names both ("hot work controls were not
            # in place ... and the work permit was not issued"): the control of
            # interest is the hot-work control, not the general authorization.
            codes = {code for _w, code, _s in scored}
            if "hot_work_controls" in codes and "work_permit" in codes:
                scored = [s for s in scored if s[1] != "work_permit"]
            scored.sort(key=lambda x: (x[0], -len(x[2])), reverse=True)
            return scored[0][1], scored[0][2], False

        # Soft inference from negation context words (e.g. "isolated",
        # "atmosphere", "vent") which can be the only barrier mention.
        ctx_best: tuple[str, str, int] = (UNKNOWN_CODE, "", 0)
        for concept in self.ontology.concepts("barrier"):
            terms = self.negation.context_terms.get(concept.code, [])
            if not terms:
                continue
            matches = [t for t in terms if f" {t} " in norm_narr]
            if matches:
                span = max(matches, key=len)
                state = self.negation.classify_barrier(concept.code,
                                                       narrative).state
                weight = 2 if state in BARRIER_FAILURE_STATES else (
                    1 if state != "unknown" else 0
                )
                # Prefer the most relevant barrier; on a tie prefer a
                # specific barrier over the energy_isolation catch-all.
                if weight > ctx_best[2] or (
                    weight == ctx_best[2] and len(span) > len(ctx_best[1])
                ):
                    ctx_best = (concept.code, span, weight)
                elif weight == ctx_best[2] and ctx_best[0] == "energy_isolation" \
                        and concept.code != "energy_isolation":
                    ctx_best = (concept.code, span, weight)
        if ctx_best[0] != UNKNOWN_CODE and ctx_best[2] >= 2:
            # A determinate failure reading of an explicit barrier outweighs
            # the energy-default guess.
            self._barrier_map.append((ctx_best[0], ctx_best[1]))
            return ctx_best[0], ctx_best[1], True

        # Soft inference from the strongest energy present.
        primary_energy = self._pick_primary(energy_codes, {
            c: "" for c in energy_codes
        }, "energy") if energy_codes else UNKNOWN_CODE
        if primary_energy in ENERGY_DEFAULT_BARRIER:
            barrier = ENERGY_DEFAULT_BARRIER[primary_energy]
            self._barrier_map.append((barrier, ""))
            return barrier, "", True

        if ctx_best[0] != UNKNOWN_CODE:
            self._barrier_map.append((ctx_best[0], ctx_best[1]))
            return ctx_best[0], ctx_best[1], True
        return UNKNOWN_CODE, "", False

    def _unsafe_action(self, barrier: str, barrier_state: str,
                       state_span: str, energy_codes: list[str]) -> str:
        if barrier in (UNKNOWN_CODE, ""):
            return "unknown"
        if barrier_state in BARRIER_FAILURE_STATES:
            basis = state_span or f"{barrier.replace('_', ' ')} not established"
            # The negation evidence span already begins with "before ..."
            # (e.g. "before cracking the bleeder needle valve..."); never double
            # the word in the rendered unsafe action.
            basis = re.sub(r"^\s*before\s+", "", basis)
            return f"work progressed before {basis}"
        if barrier_state == "verified":
            return f"work performed with {barrier.replace('_', ' ')} verified"
        return "unknown"

    def _unsafe_condition(self, energy_codes: list[str],
                          barrier_state: str) -> str:
        if energy_codes and barrier_state in BARRIER_FAILURE_STATES:
            return (
                f"{energy_codes[0].replace('_', ' ')} present "
                "without effective barrier"
            )
        return "unknown"

    def _potential_consequence(self, energy: str, exposure: str,
                               barrier_state: str) -> str:
        return inferred_potential_consequence(
            energy, exposure, barrier_state, self.ontology
        )

    def _lsr_from(self, barrier: str, energy: str, exposure: str,
                  barrier_state: str) -> list[str]:
        rules: list[str] = []
        table = self.ontology.lsr_table()
        b2r = table.get("barrier_to_rule", {})
        e2r = table.get("energy_to_rule", {})

        if barrier in b2r:
            rules.extend(b2r[barrier])
        elif energy in e2r:
            rules.extend(e2r[energy])

        if exposure == "fire_or_explosion":
            rules.append("gas_testing")
        if barrier_state == "verified":
            return []
        # dedupe preserving order
        seen: list[str] = []
        for r in rules:
            if r not in seen:
                seen.append(r)
        return seen

    def _collect_evidence(self, narrative: str, matched: dict[str, str],
                          barrier_state: str) -> list[str]:
        spans: list[str] = []
        order = ["activity", "barrier", "barrier_state", "energy", "exposure",
                 "actual_consequence", "location", "task_phase"]
        for key in order:
            span = matched.get(key)
            if span and span not in spans:
                spans.append(span)
        return spans[:20]

    def _overall_confidence(self, *values: str) -> float:
        known = sum(1 for v in values if v and v != UNKNOWN_CODE)
        total = len(values)
        return 0.4 + 0.55 * (known / total) if total else 0.4