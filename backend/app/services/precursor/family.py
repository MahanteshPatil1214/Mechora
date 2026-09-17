"""Precursor family construction.

Groups observations by structural mechanism, generates explainable family names
and summaries, and computes the prototype attention signal.
"""

from __future__ import annotations

import datetime as _dt
import itertools

from app.models.safety_event import (
    BARRIER_FAILURE_STATES,
    Observation,
    PrecursorFamily,
    UNKNOWN_CODE,
)
from app.services.normalization.ontology import Ontology
from app.services.precursor.attention import compute_attention


class FamilyBuilder:
    def __init__(self, ontology: Ontology) -> None:
        self.ontology = ontology
        templates = ontology.family_templates()
        self.templates = templates.get("templates", {})
        self.default = templates.get("default", "Barrier Review Needed")

    # ---------------------------------------------------------------- build

    def build(self, groups: list[list[Observation]], family_index: int = 0
              ) -> tuple[list[PrecursorFamily], dict[str, str]]:
        """Build families. Returns (families, obs_id -> family_id)."""
        families: list[PrecursorFamily] = []
        assignment: dict[str, str] = {}
        idx = family_index

        for group in groups:
            idx += 1
            family_id = f"PFAM-{idx:03d}"
            family = self._family_from_group(group, family_id)
            for obs in group:
                assignment[obs.id] = family_id
            families.append(family)

        return families, assignment

    def _family_from_group(self, group: list[Observation],
                           family_id: str) -> PrecursorFamily:
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
        recurring = len(group) >= 2

        exposures_known = [e.exposure for e in events
                           if e.exposure != UNKNOWN_CODE]
        exposure = exposures_known[0] if exposures_known else "unknown"

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
            sif_potential_count=sif_high_count,
            recurring=recurring,
        )

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