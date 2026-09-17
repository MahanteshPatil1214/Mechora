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
    LLMExtraction,
    Observation,
    SafetyEvent,
    UNKNOWN_CODE,
)
from app.services.evidence.evidence import EvidenceGrounder, evidence_status_for
from app.services.extraction.llm_extractor import LLMExtractor
from app.services.extraction.rule_extractor import ExtractionOutput, RuleBasedExtractor
from app.services.lsr.lsr import LSRMapper
from app.services.negation.engine import NegationEngine, split_sentences
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
    warnings: list[str] = field(default_factory=list)


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
        provider = provider or self._resolve_provider()
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

        return AnalysisResult(event=event, provider=provider, warnings=warnings)

    def to_observation(self, report_id: str, narrative: str,
                       provider: str | None = None) -> Observation:
        result = self.analyze(report_id, narrative, provider=provider)
        return Observation(
            report_id=report_id,
            narrative=narrative,
            provider=result.provider,
            event=result.event,
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
        event.potential_consequence = self.canonicalizer.map_existing(
            raw.potential_consequence, "consequence"
        )

        event.hazard = (raw.hazard or "unknown").strip()[:300] or "unknown"
        event.unsafe_action = (raw.unsafe_action or "unknown").strip()[:500] or "unknown"
        event.unsafe_condition = (raw.unsafe_condition or "unknown").strip()[:500] \
            or "unknown"

        # Negation engine is authoritative for barrier state when a barrier is known.
        if event.barrier != UNKNOWN_CODE:
            state_result = self.negation.classify_barrier(event.barrier, narrative)
            event.barrier_state = state_result.state
            event.confidence = state_result.confidence
        elif raw.barrier_state != UNKNOWN_CODE:
            event.barrier_state = raw.barrier_state
            event.confidence = 0.3

        # Actual consequence free text -> canonical if known.
        actual = raw.actual_consequence or "unknown"
        actual_code, _ = self.canonicalizer.map(actual, "consequence")
        event.actual_consequence = actual_code if actual_code != UNKNOWN_CODE else "none_identified"

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

        # Derived layers
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
            "consequence", "location", "task_phase",
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
            for i, sent in enumerate(sentences):
                if span in sent or sent in span:
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