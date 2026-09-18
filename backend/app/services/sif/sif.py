"""Prototype SIF-potential assessment (decision support).

Deterministic, explainable scoring over energy severity, exposure severity and
barrier state. This is a PROTOTYPE: never presented as accident prediction or
an OIL-approved score.
"""

from __future__ import annotations

from app.models.safety_event import (
    SIFAssessment,
    SafetyEvent,
    UNKNOWN_CODE,
)
from app.services.normalization.ontology import Ontology


class SIFAssessor:
    def __init__(self, ontology: Ontology) -> None:
        self.ontology = ontology
        rules = ontology.sif_rules().get("logic", {})
        self.penalty_states = tuple(rules.get("barrier_penalty_states", []))
        self.partial_states = tuple(rules.get("barrier_penalty_partial_states", []))
        self.penalty = float(rules.get("barrier_penalty", 2))
        self.partial_penalty = float(rules.get("partial_penalty", 1))
        self.high_threshold = float(rules.get("high_threshold", 9))
        self.medium_threshold = float(rules.get("medium_threshold", 6))
        high_energy = set(rules.get("high_energy_codes", []))
        high_exposure = set(rules.get("high_exposure_codes", []))
        self.high_energy = high_energy
        self.high_exposure = high_exposure

    def assess(self, event: SafetyEvent) -> SIFAssessment:
        energy = event.energy
        exposure = event.exposure
        barrier = event.barrier
        state = event.barrier_state

        known_fields = [
            f for f in (energy, exposure, barrier, state)
            if f != UNKNOWN_CODE
        ]
        coverage = len(known_fields) / 4.0
        confidence = round(0.35 + 0.6 * coverage, 3)

        energy_rank = self.ontology.energy_rank(energy)
        exposure_rank = self.ontology.exposure_rank(exposure)
        combined = energy_rank + exposure_rank

        score = float(combined)
        penalty_breakdown: list[str] = []

        if state in self.penalty_states:
            score += self.penalty
            penalty_breakdown.append(
                f"barrier state '{state}' adds {self.penalty:g}"
            )
        elif state in self.partial_states:
            score += self.partial_penalty
            penalty_breakdown.append("partially effective barrier adds 1")

        evidence = [
            f"energy '{energy}' severity rank {energy_rank}",
            f"exposure '{exposure}' severity rank {exposure_rank}",
            f"barrier '{barrier}' state '{state}'",
        ]
        for s in penalty_breakdown:
            evidence.append(s)

        # Transparency: attach the grounded narrative spans behind each
        # critical field, plus the consequence basis, so every YES/REVIEW is
        # backed by the actual text evidence (never inferred silently).
        field_evidence = event.field_evidence or {}
        for field, marker in (
            ("energy", "energy"),
            ("exposure", "exposure"),
            ("barrier", "barrier"),
            ("barrier_state", "barrier_state"),
        ):
            span = field_evidence.get(field)
            if span:
                evidence.append(f"grounded {marker}: \"{span}\"")
        if event.potential_consequence != UNKNOWN_CODE:
            pot_basis = event.potential_consequence_basis
            if pot_basis == "explicit":
                pot_label = "explicitly stated in the report"
            elif pot_basis == "model_inference":
                pot_label = "MODEL-INFERRED by the prototype SIF rule from grounded hazard/exposure evidence, not stated in the report"
            else:
                pot_label = "basis unknown"
            span = event.field_evidence.get("potential_consequence")
            evidence.append(
                f"potential consequence '{event.potential_consequence}' "
                f"({pot_label})"
                + (f"; narrative support: \"{span}\"" if span else "")
            )

        if state == "verified" and energy not in self.high_energy:
            return SIFAssessment(
                classification="low",
                confidence=0.85,
                basis="rule_inference",
                reason=("Barrier verified and risk controls confirmed intact; "
                        "no unmitigated SIF-potential indicators."),
                supporting_evidence=evidence,
            )

        critical_fields = ["barrier", "barrier_state", "energy", "exposure"]
        missing_critical = [
            f for f in critical_fields
            if getattr(event, f) == UNKNOWN_CODE or not getattr(event, f)
        ]

        if missing_critical:
            # A SIF YES must never rest solely on a failed barrier state.
            # Require a narrative-stated severe actual consequence, or a
            # rule-derived severe potential backed by a grounded high hazard
            # or exposure. Anything weaker is held for HSE review.
            narrative_severe = event.actual_consequence in (
                "serious_injury_or_fatality", "fatality",
            )
            # A grounded high hazard/exposure (severity rank >= 4) behind the
            # rule-inferred potential consequence justifies a YES; a failed
            # barrier state alone never does. Unknown ranks are 1, so a
            # missing hazard/exposure cannot satisfy this.
            hazard_basis = (
                self.ontology.energy_rank(event.energy) >= 4
                or self.ontology.exposure_rank(event.exposure) >= 4
            )
            inferred_severe = (
                event.potential_consequence
                in ("serious_injury_or_fatality", "fatality")
                and hazard_basis
            )
            has_direct_severe_consequence = narrative_severe or inferred_severe
            if has_direct_severe_consequence:
                return SIFAssessment(
                    classification="high",
                    confidence=round(min(0.70, 0.45 + 0.05 * (len(critical_fields) - len(missing_critical))), 3),
                    basis="explicit" if narrative_severe else "rule_inference",
                    reason=(
                        f"Grounded hazard/consequence indicators show SIF potential "
                        f"despite missing critical field(s) "
                        f"({', '.join(missing_critical)}); evidence-based, not guessed."
                    ),
                    supporting_evidence=evidence,
                )
            return SIFAssessment(
                classification="needs_review",
                confidence=round(min(0.40, 0.15 + 0.05 * (len(critical_fields) - len(missing_critical))), 3),
                basis="needs_review",
                reason=f"Insufficient critical evidence ({', '.join(missing_critical)}) to assess SIF potential with certainty. Held for HSE human review.",
                supporting_evidence=evidence,
            )

        if score >= self.high_threshold or (
            state in self.penalty_states
            and energy in self.high_energy
            and exposure in self.high_exposure
        ):
            classification = "high"
            reason = (
                "High-hazard energy combined with an ineffective barrier state "
                "and active exposure indicators."
            )
            confidence = 0.88
        elif score >= self.medium_threshold:
            classification = "medium"
            reason = (
                "Moderate energy/exposure with a not-fully-effective barrier "
                "state indicates medium SIF potential."
            )
            confidence = 0.75
        else:
            if state in self.penalty_states:
                classification = "needs_review"
                reason = (
                    "Barrier failure state deters a low classification "
                    "without HSE review."
                )
                confidence = 0.50
            else:
                classification = "low"
                reason = (
                    "No strong combination of hazardous energy, exposure and barrier "
                    "failure indicates low SIF potential."
                )
                confidence = 0.80

        if event.potential_consequence in (
            "serious_injury_or_fatality", "fatality",
        ) and classification in ("low", "medium"):
            classification = "high"
            confidence = max(confidence, 0.85)
            reason = (
                "Rule-grounded consequence potential (serious injury or "
                "fatality inferred from hazard/exposure evidence) elevates "
                "SIF potential."
            )

        return SIFAssessment(
            classification=classification,
            confidence=confidence,
            basis=(
                "explicit"
                if event.actual_consequence in (
                    "serious_injury_or_fatality", "fatality",
                )
                else "rule_inference"
            ),
            reason=reason,
            supporting_evidence=evidence,
        )