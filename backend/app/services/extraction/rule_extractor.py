"""Deterministic (rule-based) extraction service.

Offline fallback that mirrors the strict LLM extraction schema. Used when no
Gemini key is available so the full pipeline, tests and evaluation run
reproducibly. It grounds every field in narrative text and never invents
values: unmatched fields become ``unknown``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.safety_event import (
    LLMExtraction,
    BARRIER_FAILURE_STATES,
    UNKNOWN_CODE,
)
from app.services.evidence.evidence import EvidenceGrounder
from app.services.negation.engine import NegationEngine
from app.services.normalization.canonical import Canonicalizer
from app.services.normalization.ontology import Ontology, normalize_text


@dataclass
class ExtractionOutput:
    extraction: LLMExtraction
    matched: dict[str, str] = field(default_factory=dict)
    multi_energies: list[dict[str, Any]] = field(default_factory=list)
    multi_barriers: list[dict[str, Any]] = field(default_factory=list)
    provider: str = "rules"


# Energy -> required barrier inference when no barrier word is mentioned.
ENERGY_DEFAULT_BARRIER = {
    "pressurized_gas": "energy_isolation",
    "electrical_energy": "energy_isolation",
    "stored_mechanical_energy": "energy_isolation",
    "thermal_energy": "energy_isolation",
    "flammable_atmosphere": "hot_work_controls",
    "chemical_exposure": "chemical_handling_controls",
    "gravity": "fall_protection",
    "moving_equipment": "machinery_guarding",
}


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
        matched["activity"] = a_span

        task_phase, t_span = self.canonicalizer.map(narrative, "task_phase")
        matched["task_phase"] = t_span

        energies, en_spans = self._detect_category(narrative, "energy")
        if not energies and activity == "hot_work":
            energies = ["flammable_atmosphere"]
            en_spans = {"flammable_atmosphere": "hot work"}
        primary_energy = self._pick_primary(energies, en_spans, "energy")
        matched["energy"] = en_spans.get(primary_energy, "")
        energy_codes = [e for e in energies]

        # Task-phase inference: a known activity always implies an active job
        # ("maintenance"); unknown activity uses pre/post job temporal cues
        # or verification-condition patterns (the classic negation-sentence
        # forms like "X was not confirmed").  Phrases that name specific
        # activities ("cleaning", "testing") are suppressed when activity is
        # unknown so the pre/post heuristics can take over.
        if activity and activity != UNKNOWN_CODE:
            task_phase = "maintenance"
            t_span = ""
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
                t_span = ""
            elif any(t in norm for t in post_words):
                task_phase = "post_job"
                t_span = ""

        exposure, ex_span = self._exposure_for(narrative, norm)
        matched["exposure"] = ex_span

        barrier, bar_span, inferred = self._detect_barrier(
            narrative, norm, energy_codes
        )
        matched["barrier"] = bar_span

        # Barrier state: negation engine is authoritative.
        state_result = self.negation.classify_barrier(barrier, narrative)
        barrier_state = state_result.state
        matched["barrier_state"] = state_result.evidence_span
        state_confidence = state_result.confidence

        consequence, c_span = self._detect_category2(narrative, "consequence")
        matched["consequence"] = c_span

        location, l_span = self.canonicalizer.map(narrative, "location")
        matched["location"] = l_span

        unsafe_action = self._unsafe_action(
            barrier, barrier_state, state_result.evidence_span, energy_codes
        )
        unsafe_condition = self._unsafe_condition(energy_codes, barrier_state)

        potential = self._potential_consequence(
            primary_energy, exposure, barrier_state
        )

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
            actual_consequence=consequence if consequence != UNKNOWN_CODE
            else "none_identified",
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
        return (code, best) if best else ("", "")

    def _pick_primary(self, codes: list[str], spans: dict[str, str],
                      category: str) -> str:
        if not codes:
            return UNKNOWN_CODE
        if category == "energy":
            ranked = sorted(
                codes,
                key=lambda c: (
                    self.ontology.energy_rank(c),
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
            c_code, c_span = self._best_synonym_match(narrative, "exposure",
                                                      concept.code)
            if c_code:
                rank = self.ontology.exposure_rank(c_code)
                if rank > best_rank or (rank == best_rank and c_span):
                    best = c_code
                    best_rank = rank
                    best_span = c_span
        return best, best_span

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
        if barrier_state in BARRIER_FAILURE_STATES:
            if self.ontology.energy_rank(energy) >= 4:
                return "serious_injury_or_fatality"
            return "injury"
        if energy != UNKNOWN_CODE:
            if self.ontology.energy_rank(energy) >= 4:
                return "serious_injury_or_fatality"
            return "injury"
        return "unknown"

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
                 "consequence", "location", "task_phase"]
        for key in order:
            span = matched.get(key)
            if span and span not in spans:
                spans.append(span)
        if barrier_state in ("not_verified", "failed", "absent",
                             "partially_effective") and matched.get("barrier_state"):
            pass
        return spans[:20]

    def _overall_confidence(self, *values: str) -> float:
        known = sum(1 for v in values if v and v != UNKNOWN_CODE)
        total = len(values)
        return 0.4 + 0.55 * (known / total) if total else 0.4