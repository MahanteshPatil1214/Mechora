"""Precursor family construction.

Groups observations by structural mechanism, generates explainable family names
and summaries, and computes the prototype attention signal.
"""

from __future__ import annotations

import datetime as _dt
import itertools
from collections import Counter

from app.models.safety_event import (
    BARRIER_FAILURE_STATES,
    GroupingEvidence,
    Observation,
    PrecursorFamily,
    UNKNOWN_CODE,
)
from app.services.normalization.ontology import Ontology
from app.services.precursor.attention import compute_attention

# Structural dimensions used for WHY GROUPED? evidence (weight-bearing dims
# plus signal indicators). Order matches the PRD priority feel.
GROUPING_DIMENSIONS = (
    ("energy", "energy"),
    ("barrier", "barrier"),
    ("barrier_state", "barrier_state"),
    ("exposure", "exposure"),
    ("task_phase", "task_phase"),
    ("activity", "activity"),
    ("potential_consequence", "potential_consequence"),
)


class FamilyBuilder:
    def __init__(self, ontology: Ontology) -> None:
        self.ontology = ontology
        templates = ontology.family_templates()
        self.templates = templates.get("templates", {})
        self.default = templates.get("default", "Barrier Review Needed")

    # ---------------------------------------------------------------- build

    def build(self, groups: list[list[Observation]], family_index: int = 0,
              recurring_threshold: int = 2
              ) -> tuple[list[PrecursorFamily], dict[str, str]]:
        """Build families. Returns (families, obs_id -> family_id)."""
        families: list[PrecursorFamily] = []
        assignment: dict[str, str] = {}
        idx = family_index

        for group in groups:
            idx += 1
            family_id = f"PFAM-{idx:03d}"
            family = self._family_from_group(group, family_id,
                                             recurring_threshold)
            for obs in group:
                assignment[obs.id] = family_id
            families.append(family)

        return families, assignment

    def _family_from_group(self, group: list[Observation],
                           family_id: str,
                           recurring_threshold: int = 2) -> PrecursorFamily:
        events = [o.event for o in group]

        mechanism = self._dominant(events, "barrier")
        state = self._dominant(events, "barrier_state")
        energy = self._dominant(events, "energy")
        exposure = self._dominant(events, "exposure")

        barriers_known = [e.barrier for e in events if e.barrier != UNKNOWN_CODE]
        barrier = barriers_known[0] if barriers_known else "unknown"
        states_known = [e.barrier_state for e in events
                        if e.barrier_state != UNKNOWN_CODE]
        state = states_known[0] if states_known else "unknown"
        energies_known = [e.energy for e in events if e.energy != UNKNOWN_CODE]
        energy = energies_known[0] if energies_known else "unknown"

        name = self._name(barrier, state)

        activities = sorted({e.activity for e in events
                             if e.activity != UNKNOWN_CODE})
        locations = sorted({e.location for e in events
                            if e.location != UNKNOWN_CODE})
        hazards = sorted({e.hazard for e in events
                          if e.hazard and e.hazard != "unknown"})

        attention = compute_attention(group)

        sif_high_count = sum(
            1 for e in events if e.sif.classification == "high"
        )
        recurring = len(group) >= recurring_threshold

        exposures_known = [e.exposure for e in events
                           if e.exposure != UNKNOWN_CODE]
        exposure = exposures_known[0] if exposures_known else "unknown"

        grouping_evidence = self._grouping_evidence(events)

        parts = [
            f"{len(group)} observation(s).",
        ]
        if barrier != UNKNOWN_CODE:
            parts.append(
                f"Common barrier: {self.ontology.label('barrier', barrier)} "
                f"(state: {self.ontology.label('barrier_state', state)})."
            )
        if energy != UNKNOWN_CODE:
            parts.append(
                f"Common hazard/energy: {self.ontology.label('energy', energy)}."
            )
        if exposure != UNKNOWN_CODE:
            parts.append(
                f"Common exposure: {self.ontology.label('exposure', exposure)}."
            )
        description = " ".join(parts)

        return PrecursorFamily(
            id=family_id,
            name=name,
            description=description,
            observation_ids=[o.id for o in group],
            common_barrier=barrier,
            common_barrier_state=state,
            common_energy=energy,
            common_exposure=exposure,
            activities=activities,
            locations=locations,
            hazard="; ".join(hazards),
            attention_signal=attention["score"],
            attention_basis=attention["basis"],
            attention_factors=attention["factors"],
            sif_potential_count=sif_high_count,
            recurring=recurring,
            recurring_threshold=recurring_threshold,
            grouping_evidence=grouping_evidence,
        )

    def _grouping_evidence(self, events) -> list[GroupingEvidence]:
        """WHY GROUPED? — per-dimension agreement computed from the actual
        observation set inside this family (never hardcoded)."""
        out: list[GroupingEvidence] = []
        n = len(events)
        for dimension, attr in GROUPING_DIMENSIONS:
            known: list[str] = []
            for e in events:
                value = getattr(e, attr)
                if value and value != UNKNOWN_CODE:
                    known.append(value)
            if not known:
                out.append(GroupingEvidence(
                    dimension=dimension,
                    value="",
                    status="distinct",
                    coverage=0.0,
                    note="No common value extracted",
                ))
                continue
            counts = Counter(known)
            dominant, count = counts.most_common(1)[0]
            # Deterministic tie-break on ties: prefer the alphabetically last
            # code so the family is stable regardless of dict ordering.
            coverage = round(count / n, 4)
            if coverage == 1.0:
                status = "same"
            elif coverage >= 0.5:
                status = "mixed"
            else:
                status = "distinct"
            label = self._label(dimension, dominant)
            out.append(GroupingEvidence(
                dimension=dimension,
                value=dominant,
                status=status,
                coverage=coverage,
                note=(
                    f"{label} in {count}/{n} observation(s)"
                    if status == "same" else
                    f"{label} dominant ({count}/{n}), "
                    f"{n - count} differ"
                ),
            ))
        return out

    def _label(self, dimension: str, code: str) -> str:
        category = "consequence" if dimension == "potential_consequence" \
            else dimension
        try:
            return self.ontology.label(category, code)
        except Exception:  # noqa: BLE001
            return code.replace("_", " ").title()

    def _dominant(self, events, field: str) -> str:
        counter: dict[str, int] = {}
        for e in events:
            value = getattr(e, field)
            if value and value != UNKNOWN_CODE:
                counter[value] = counter.get(value, 0) + 1
        if not counter:
            return UNKNOWN_CODE
        top = max(
            counter.items(),
            key=lambda kv: (kv[1], -_code_len(kv[0])),
        )
        return top[0]

    def _name(self, barrier: str, state: str) -> str:
        by_barrier = self.templates.get(barrier, {})
        if isinstance(by_barrier, dict):
            return by_barrier.get(state, self.default)
        return self.default


def _code_len(code: str) -> int:
    return len(code)