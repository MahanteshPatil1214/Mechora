"""End-to-end safety analysis pipeline.

Raw narrative -> (LLM or rule) extraction -> schema validation -> negation
engine (authoritative) -> canonical normalization -> evidence grounding ->
precursor signature -> SIF assessment -> LSR mapping.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.config import Settings
from app.models.safety_event import (
    BARRIER_FAILURE_STATES,
    LLMExtraction,
    Observation,
    SafetyEvent,
    UNKNOWN_CODE,
)
from app.services.evidence.evidence import EvidenceGrounder, evidence_status_for
from app.services.extraction.llm_extractor import LLMExtractor
from app.services.extraction.rule_extractor import (
    ExtractionOutput,
    RuleBasedExtractor,
    inferred_potential_consequence,
)
from app.services.lsr.lsr import LSRMapper
from app.services.negation.engine import (
    NegationEngine,
    sentence_containing,
    split_sentences,
)
from app.services.normalization.canonical import Canonicalizer
from app.services.normalization.ontology import Ontology
from app.services.precursor.similarity import build_signature
from app.services.sif.sif import SIFAssessor

logger = logging.getLogger("mechora.pipeline")

CATEGORY_FIELDS = {
    "activity": "activity",
    "task_phase": "task_phase",
    "energy": "energy",
    "barrier": "barrier",
    "exposure": "exposure",
    "location": "location",
    "consequence": "potential_consequence",
}


@dataclass
class AnalysisResult:
    event: SafetyEvent
    provider: str = "rules"
    resolved_provider: str = ""
    warnings: list[str] = field(default_factory=list)
    # Extraction provenance: what was asked for, what actually ran, and — when
    # an LLM pass was genuinely attempted but failed — why the deterministic
    # extractor was used. 'auto' is a resolution target, not a fallback.
    requested_provider: str = "auto"
    fallback_used: bool = False
    fallback_reason: str = ""


class AnalysisPipeline:
    def __init__(self, ontology: Ontology, settings: Settings) -> None:
        self.ontology = ontology
        self.settings = settings
        self.canonicalizer = Canonicalizer(ontology)
        self.negation = NegationEngine(ontology)
        self.grounder = EvidenceGrounder()
        self.rule_extractor = RuleBasedExtractor(
            ontology, self.canonicalizer, self.negation, self.grounder
        )
        self.llm_extractor = LLMExtractor(ontology, settings)
        self.sif = SIFAssessor(ontology)
        self.lsr = LSRMapper(ontology)

    # ---------------------------------------------------------------- public

    def analyze(self, report_id: str, narrative: str,
                provider: str | None = None) -> AnalysisResult:
        requested = provider or self._resolve_provider()
        provider = requested
        extraction_output: ExtractionOutput | None = None
        raw: LLMExtraction | None = None
        warnings: list[str] = []

        if provider == "llm":
            try:
                raw, meta = self.llm_extractor.extract(report_id, narrative)
                provider = "llm"
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM extraction failed (%s); using rules.", exc)
                warnings.append(
                    "Gemini extraction unavailable; deterministic extractor used."
                )
                provider = "rules"

        if provider == "rules":
            extraction_output = self.rule_extractor.extract(report_id, narrative)
            raw = extraction_output.extraction
            provider = "rules"

        event = self._build_event(report_id, narrative, raw, extraction_output)

        fallback_used = requested == "llm" and provider == "rules"
        fallback_reason = (
            "LLM extraction failed at runtime; deterministic extractor used"
            if fallback_used else ""
        )

        return AnalysisResult(
            event=event,
            provider=provider,
            resolved_provider=provider,
            warnings=warnings,
            requested_provider=requested,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def to_observation(self, report_id: str, narrative: str,
                       provider: str | None = None,
                       document_id: str = "",
                       report_segment_id: str = "",
                       segment_index: int | None = None,
    report_type: str | None = None) -> Observation:
        result = self.analyze(report_id, narrative, provider=provider)
        return Observation(
            report_id=report_id,
            narrative=narrative,
            provider=result.provider,
            requested_provider=result.requested_provider,
            fallback_used=result.fallback_used,
            fallback_reason=result.fallback_reason,
            event=result.event,
            document_id=document_id,
            report_segment_id=report_segment_id,
            segment_index=segment_index,
            report_type=report_type or "unknown",
        )

    # --------------------------------------------------------------- internal

    def _resolve_provider(self) -> str:
        mode = self.settings.extraction_provider
        if mode == "llm":
            return "llm"
        if mode == "rules":
            return "rules"
        # auto
        if self.settings.gemini_api_key:
            return "llm"
        return "rules"

    def _build_event(self, report_id: str, narrative: str,
                     raw: LLMExtraction,
                     output: ExtractionOutput | None) -> SafetyEvent:
        event = SafetyEvent(report_id=report_id, narrative=narrative)

        event.activity = self.canonicalizer.map_existing(raw.activity, "activity")
        event.task_phase = self.canonicalizer.map_existing(raw.task_phase, "task_phase")
        event.energy = self.canonicalizer.map_existing(raw.energy, "energy")
        event.barrier = self.canonicalizer.map_existing(raw.barrier, "barrier")
        event.exposure = self.canonicalizer.map_existing(raw.exposure, "exposure")
        event.location = self.canonicalizer.map_existing(raw.location, "location")

        event.hazard = (raw.hazard or "unknown").strip()[:300] or "unknown"
        event.unsafe_action = (raw.unsafe_action or "unknown").strip()[:500] or "unknown"
        event.unsafe_condition = (raw.unsafe_condition or "unknown").strip()[:500] \
            or "unknown"

        # Negation engine is authoritative for barrier state when a barrier is known.
        barrier_state_span = ""
        if event.barrier != UNKNOWN_CODE:
            state_result = self.negation.classify_barrier(event.barrier, narrative)
            event.barrier_state = state_result.state
            event.confidence = state_result.confidence
            # Barrier-state evidence = FULL causal sentence carrying the
            # verification phrase (same attribution rule as the rules path).
            barrier_state_span = sentence_containing(
                narrative, state_result.evidence_span or ""
            ) or ""
        elif raw.barrier_state != UNKNOWN_CODE:
            event.barrier_state = raw.barrier_state
            event.confidence = 0.3

        # Exposure integrity guard (all providers): a RELEASE exposure is only
        # legitimate when the narrative literally states a release/escape (a
        # grounded span exists). A verified / positive-control narrative that
        # does NOT state a release must never surface an invented "Uncontrolled
        # Gas Release" — exposure stays Unknown unless explicitly grounded.
        # This neutralises LLM hallucination, and the rules path already
        # negates "no gas was released", so only genuinely grounded releases
        # survive.
        if event.barrier_state == "verified" and event.exposure not in (
            UNKNOWN_CODE, "unknown"
        ):
            release_span = ""
            if output is not None:
                release_span = (output.matched or {}).get("exposure", "")
            else:
                release_span = self.rule_extractor.verbatim_span_for_code(
                    narrative, "exposure", event.exposure
                )
            if not release_span:
                event.exposure = "unknown"

        # Potential consequence is deterministic and rule-grounded: it is
        # recomputed authoritatively from the final canonical hazard/exposure/
        # barrier-state so no provider (LLM) can invent an ungrounded SIF
        # potential. Unknown hazard AND exposure -> unknown consequence.
        event.potential_consequence = inferred_potential_consequence(
            event.energy,
            event.exposure,
            event.barrier_state,
            self.ontology,
        )

        # Actual consequence: populated ONLY from an explicit narrative
        # statement ("No injury occurred." -> none_identified + explicit span;
        # "could have been fatal" -> serious_injury_or_fatality). When nothing
        # is stated, the value is UNKNOWN — the "none_identified" default would
        # falsely imply a consequence was considered and ruled out.
        # Deterministic actual-consequence detection (negation-aware) is ALWAYS
        # computed: the rules path uses it directly and the LLM path uses it to
        # keep a negated-consequence narrative ("No injury occurred and no
        # medical treatment was required.") grounded the SAME way — the model
        # proposes a value, but only a verbatim non-negated / all-negated
        # reading ever becomes explicit evidence.
        det_consequence, det_span = (
            self.rule_extractor.detect_actual_consequence(narrative)
        )
        actual = raw.actual_consequence or "unknown"
        if self.ontology.is_known("consequence", actual):
            # Already-canonical code (e.g. none_identified or a code an LLM
            # returned verbatim): use it directly; a natural-language phrase
            # would be mapped below instead.
            actual_code, actual_span = actual, ""
        else:
            actual_code, actual_span = self.canonicalizer.map(actual, "consequence")
        _actual_span = (
            (output.matched or {}).get("actual_consequence")
            if output is not None else actual_span
        )
        if actual_code == UNKNOWN_CODE:
            event.actual_consequence = "unknown"
        elif (
            not _actual_span and actual_code == "none_identified"
            and actual in ("", "unknown", "none_identified", "no consequence")
        ):
            # "No consequence identified" is honest ONLY when the text actually
            # negates the consequence (deterministic, negation-aware). Otherwise
            # an unstated consequence must not masquerade as none_identified.
            if det_consequence == "none_identified" and det_span:
                event.actual_consequence = "none_identified"
                _actual_span = det_span
            else:
                event.actual_consequence = "unknown"
        else:
            event.actual_consequence = actual_code
        # LLM path: a model-proposed POSITIVE consequence is only explicit when
        # a verbatim NON-negated span supports it (deterministic attribution).
        if output is None and event.actual_consequence not in (
            "", UNKNOWN_CODE, "none_identified"
        ):
            _pos_span = self.rule_extractor.verbatim_span_for_code(
                narrative, "consequence", event.actual_consequence
            )
            if _pos_span and not _actual_span:
                _actual_span = _pos_span

        # LSR list from LLM must be canonical & deduped; deterministic mapper
        # recomputes authoritative mapping afterwards anyway.
        rules = [r for r in raw.life_saving_rules
                 if self.ontology.is_known_lsr(r)]
        event.life_saving_rules = list(dict.fromkeys(rules))

        event.evidence = self._ground_evidence(narrative, raw, output)

        grounded = [e for e in event.evidence if e.status == "grounded"]
        event.evidence_status = "grounded" if grounded else "unknown"

        if output is not None:
            event.confidence = raw.confidence
            # Per-attribute supporting spans (rules path only; grounded text).
            fev = {k: v for k, v in (output.matched or {}).items() if v}
            if "consequence" in fev:
                fev["actual_consequence"] = fev.pop("consequence")
            event.field_evidence = fev
        else:
            # LLM path: the model may only propose VALUES. Evidence
            # attribution is recomputed deterministically from the canonical
            # event via the ontology, so EXPLICIT vs INFERRED provenance never
            # depends on what the model emitted — language understanding is
            # Gemini's job; evidence grounding is the pipeline's.
            fev = {}
            for _f in (
                "activity", "task_phase", "energy", "barrier",
                "exposure", "location",
            ):
                _sp = self.rule_extractor.verbatim_span_for_code(
                    narrative, _f, getattr(event, _f)
                )
                if _sp:
                    fev[_f] = _sp
            if barrier_state_span:
                fev["barrier_state"] = barrier_state_span
        if _actual_span and not fev.get("actual_consequence"):
            fev["actual_consequence"] = _actual_span
        event.field_evidence = fev

        # Potential-consequence basis: 'explicit' ONLY when the narrative
        # literally states the exact same consequence code; otherwise it is
        # 'model_inference' (documented prototype rule over grounded hazard/
        # exposure) and must never carry fabricated textual evidence. A
        # literal severe-outcome statement ("could have been fatal") with no
        # hazard phrase is still surfaced as an explicit potential.
        _pot = event.potential_consequence
        explicit_span = _actual_span or ""
        if _pot not in (UNKNOWN_CODE, "none_identified", ""):
            if explicit_span and event.actual_consequence == _pot:
                event.potential_consequence_basis = "explicit"
                if not event.field_evidence.get("potential_consequence"):
                    event.field_evidence["potential_consequence"] = \
                        event.field_evidence.get("actual_consequence", "")
            else:
                event.potential_consequence_basis = "model_inference"
        elif explicit_span and event.actual_consequence in (
                "serious_injury_or_fatality", "fatality"):
            event.potential_consequence = event.actual_consequence
            event.potential_consequence_basis = "explicit"
            event.field_evidence["potential_consequence"] = explicit_span
        else:
            event.potential_consequence_basis = "unknown"
        # Per-field EXPLICIT vs INFERRED provenance: a value is 'explicit'
        # only when a verbatim narrative span supports it; a normalized or
        # rule-derived value without a direct span is 'inferred' and must
        # never be presented as if it were quoted from the report.
        for _f in (
            "activity", "task_phase", "energy", "barrier", "barrier_state",
            "exposure", "actual_consequence", "location",
        ):
            _val = getattr(event, _f)
            if _val in ("", "unknown", UNKNOWN_CODE):
                event.field_basis[_f] = "unknown"
            elif event.field_evidence.get(_f):
                event.field_basis[_f] = "explicit"
            else:
                event.field_basis[_f] = "inferred"
        event.field_basis["potential_consequence"] = event.potential_consequence_basis
        # Derived layers
        # Unknown critical fields -> NEEDS_REVIEW (PRD / Safety Logic)
        CRITICAL_FIELDS = ("barrier", "barrier_state", "energy", "exposure")
        missing_critical = [
            f for f in CRITICAL_FIELDS
            if getattr(event, f) == UNKNOWN_CODE or not getattr(event, f)
        ]
        if event.barrier_state == "verified" and "exposure" in missing_critical:
            missing_critical.remove("exposure")
        event.missing_fields = missing_critical
        event.needs_review = bool(missing_critical)

        event.precursor_signature = build_signature(event)
        event.sif = self.sif.assess(event)
        mapping = self.lsr.map(event)
        event.lsr_mapping = mapping
        event.life_saving_rules = mapping.rules

        return event

    def _ground_evidence(self, narrative: str, raw: LLMExtraction,
                         output: ExtractionOutput | None) -> list:
        """Build grounded evidence records, deduplicating spans."""
        sentences = split_sentences(narrative)
        spans: list[str] = []
        matched = (output.matched if output else {})

        ordered_keys = [
            "activity", "barrier", "barrier_state", "energy", "exposure",
            "actual_consequence", "location", "task_phase",
        ]
        for key in ordered_keys:
            span = matched.get(key, "")
            if span and span not in spans:
                spans.append(span)

        for span in raw.evidence:
            span = (span or "").strip()
            if span and span not in spans:
                spans.append(span)

        evidence_records = []
        for span in spans:
            if not span:
                continue
            status = "grounded"
            idx = -1
            s_low = span.lower()
            for i, sent in enumerate(sentences):
                sent_low = sent.lower()
                if s_low in sent_low or sent_low in s_low:
                    idx = i
                    break
            if idx == -1:
                status = "needs_review"
            evidence_records.append({
                "span": span,
                "sentence_index": idx,
                "source": "narrative",
                "status": status,
            })
        from app.models.safety_event import Evidence
        return [Evidence(**r) for r in evidence_records]


# Shared lazily-initialized pipeline. Every analysis route (manual JSON input or
# uploaded documents) funnels through this single instance so extraction,
# evidence grounding and persistence behave identically everywhere.
_pipeline_instance: AnalysisPipeline | None = None


def get_pipeline(settings=None) -> AnalysisPipeline:
    """Return the shared :class:`AnalysisPipeline` (created on first call)."""
    global _pipeline_instance
    if _pipeline_instance is None:
        from app.config import get_settings
        from app.services.normalization.ontology import get_ontology

        _pipeline_instance = AnalysisPipeline(
            get_ontology(), settings or get_settings()
        )
    return _pipeline_instance