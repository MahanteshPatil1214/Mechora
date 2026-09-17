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

        if state == "verified" and energy not in self.high_energy:
            return SIFAssessment(
                classification="low",
                confidence=round(max(confidence, 0.7), 3),
                reason=("Barrier verified and no high-energy exposure; "
                        "no SIF-potential indicators."),
                supporting_evidence=evidence,
            )

        is_high_exposure = exposure in self.high_exposure or energy in self.high_energy
        if coverage < 0.5 and not is_high_exposure:
            return SIFAssessment(
                classification="needs_review",
                confidence=round(min(confidence, 0.4), 3),
                reason=("Insufficient structured evidence "
                        "(energy/exposure/barrier unknowns) to assess SIF potential."),
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
                "and serious exposure indicators."
            )
        elif score >= self.medium_threshold:
            classification = "medium"
            reason = (
                "Moderate energy/exposure with a not-fully-effective barrier "
                "state indicates medium SIF potential."
            )
        else:
            classification = "low"
            reason = (
                "No strong combination of hazardous energy, exposure and barrier "
                "failure indicates low SIF potential."
            )

        if event.potential_consequence in (
            "serious_injury_or_fatality", "fatality",
        ) and classification in ("low", "medium"):
            classification = "high"
            reason = (
                "Narrative-level consequence indicators "
                "(serious injury or fatality) raise SIF potential."
            )

        if state in ("not_verified", "failed", "absent") and classification == "low":
            classification = "needs_review"
            reason = (
                "Barrier failure states deters a low classification "
                "without HSE review."
            )

        return SIFAssessment(
            classification=classification,
            confidence=confidence,
            reason=reason,
            supporting_evidence=evidence,
        )