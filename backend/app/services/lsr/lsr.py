"""Explainable IOGP Life-Saving Rule mapping (FR-10).

Deterministic mapping from a detected barrier/energy to the relevant IOGP
Life-Saving Rule(s). Where confidence is insufficient the mapping returns
``needs_review`` instead of forcing a rule.
"""

from __future__ import annotations

from app.models.safety_event import LSRMapping, SafetyEvent, UNKNOWN_CODE
from app.services.normalization.ontology import Ontology


class LSRMapper:
    def __init__(self, ontology: Ontology) -> None:
        self.ontology = ontology
        table = ontology.lsr_table()
        self.rules = table.get("rules", [])
        self.barrier_to_rule = table.get("barrier_to_rule", {})
        self.energy_to_rule = table.get("energy_to_rule", {})
        self._labels = {r["code"]: r["label"] for r in self.rules}

    def rule_labels(self) -> dict[str, str]:
        return self._labels

    def map(self, event: SafetyEvent) -> LSRMapping:
        basis_parts: list[str] = []
        evidence: list[str] = []
        rules: list[str] = []
        confidence = 0.0

        # Barrier-rules are authoritative when a barrier is known; energy
        # rules only substitute when no barrier maps (GT convention).
        if event.barrier != UNKNOWN_CODE:
            mapped = self.barrier_to_rule.get(event.barrier, [])
            if mapped:
                rules.extend(mapped)
                basis_parts.append(
                    f"barrier '{event.barrier}' -> "
                    + ", ".join(self._labels.get(r, r) for r in mapped)
                )
                confidence = 0.92 if event.barrier_state != "verified" else 0.6
            else:
                mapped = self.energy_to_rule.get(event.energy, [])
                if mapped:
                    rules.extend(mapped)
                    basis_parts.append(
                        f"energy '{event.energy}' -> "
                        + ", ".join(self._labels.get(r, r) for r in mapped)
                    )
                    confidence = max(confidence, 0.85)
        elif event.energy != UNKNOWN_CODE:
            mapped = self.energy_to_rule.get(event.energy, [])
            if mapped:
                rules.extend(mapped)
                basis_parts.append(
                    f"energy '{event.energy}' -> "
                    + ", ".join(self._labels.get(r, r) for r in mapped)
                )
                confidence = max(confidence, 0.85)

        if event.exposure == "fire_or_explosion":
            rules.append("gas_testing")
            basis_parts.append("fire/explosion exposure -> Gas Testing")

        deduped: list[str] = []
        for r in rules:
            if r not in deduped:
                deduped.append(r)

        if event.evidence:
            evidence = [e.span for e in event.evidence if e.span][:5]

        if not deduped:
            return LSRMapping(
                rules=[],
                confidence=0.0,
                basis="Insufficient evidence to map a Life-Saving Rule.",
                evidence=evidence,
                needs_review=True,
            )

        return LSRMapping(
            rules=deduped,
            confidence=round(min(1.0, confidence), 3),
            basis="; ".join(basis_parts),
            evidence=evidence,
            needs_review=False,
        )