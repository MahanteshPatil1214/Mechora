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
# plus signal indicators). Order matches the PRD priority feel. NOTE: only
# dimensions that actually participate in structural clustering are listed;
# potential_consequence is derived from energy/exposure/state (not a grouping
# weight) and is deliberately excluded so WHY GROUPED never claims a
# non-clustering dimension caused grouping.
GROUPING_DIMENSIONS = (
    ("energy", "energy"),
    ("barrier", "barrier"),
    ("barrier_state", "barrier_state"),
    ("exposure", "exposure"),
    ("task_phase", "task_phase"),
    ("activity", "activity"),
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
        """Build families. Returns (families, obs_id -> family_id).

        ``family_index`` is accepted for backward compatibility but IGNORED:
        family IDs are derived deterministically from the structural mechanism
        signature, so the same mechanism always keeps the same family id no
        matter how many observations are inserted, filtered or re-sorted.
        """
        families: list[PrecursorFamily] = []
        assignment: dict[str, str] = {}
        for group in groups:
            family = self._family_from_group(group, recurring_threshold)
            for obs in group:
                assignment[obs.id] = family.id
            families.append(family)

        return families, assignment

    @staticmethod
    def _family_id(barrier: str, state: str, energy: str,
                   exposure: str) -> str:
        """Deterministic, stable, unique family id derived from the mechanism
        signature (barrier + barrier_state + energy + exposure). Distinct
        structural families always differ in at least one of these core
        fields, so the hash is collision-safe within the clustering result.
        """
        import hashlib

        key = "||".join(
            (code or "unknown").strip().lower()
            for code in (barrier, state, energy, exposure)
        )
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return f"PFAM-{digest[:5].upper()}"

    def _family_from_group(self, group: list[Observation],
                           recurring_threshold: int = 2) -> PrecursorFamily:
        events = [o.event for o in group]

        barriers_known = [e.barrier for e in events if e.barrier != UNKNOWN_CODE]
        barrier = barriers_known[0] if barriers_known else "unknown"
        states_known = [e.barrier_state for e in events
                        if e.barrier_state != UNKNOWN_CODE]
        state = states_known[0] if states_known else "unknown"

        # Structural Precursor Principle: Only assign a family-level common
        # energy or exposure if a solid majority of member observations
        # explicitly share that attribute. Never infer a family-level exposure
        # when reports have Unknown or divergent exposures.
        energy = self._dominant(events, "energy", require_majority=True)
        exposure = self._dominant(events, "exposure", require_majority=True)

        family_id = self._family_id(barrier, state, energy, exposure)

        if state == "verified":
            family_type = "controlled"
        elif state in ("unknown", "needs_review") or barrier in ("unknown", "needs_review"):
            family_type = "needs_review"
        else:
            family_type = "precursor"

        name = self._name(barrier, state)

        activities = sorted({e.activity for e in events
                             if e.activity != UNKNOWN_CODE})
        locations = sorted({e.location for e in events
                            if e.location != UNKNOWN_CODE})
        hazards = sorted({e.hazard for e in events
                          if e.hazard and e.hazard != "unknown"})

        dominant_phase = self._dominant(events, "task_phase", require_majority=False)

        core_mechanism = {
            "energy": energy,
            "barrier": barrier,
            "barrier_state": state,
            "exposure": exposure,
        }

        context = {
            "task_phase": dominant_phase,
            "activities": activities,
            "locations": locations,
            "distinct_activities_count": len(activities),
            "distinct_locations_count": len(locations),
        }

        recurring = len(group) >= recurring_threshold

        recurrence = {
            "observation_count": len(group),
            "distinct_activities_count": len(activities),
            "distinct_locations_count": len(locations),
            "is_recurring": recurring,
            "recurring_threshold": recurring_threshold,
            "status": "recurring" if recurring else "single",
            "label": "recurring" if recurring else "single / not established",
        }

        if family_type == "precursor":
            barrier_label = self.ontology.label("barrier", barrier)
            state_label = self.ontology.label("barrier_state", state)
            energy_label = self.ontology.label("energy", energy)
            if len(activities) > 1:
                act_names = ", ".join(
                    self.ontology.label("activity", a) for a in activities[:3]
                )
                if recurring:
                    why_it_matters = (
                        f"{len(group)} observations reveal the same failed barrier "
                        f"({barrier_label}: {state_label}) recurring across "
                        f"{len(activities)} distinct activities ({act_names}). "
                        f"While the work equipment varies, the underlying mechanism "
                        f"is identical: work involving {energy_label} without "
                        f"verified barrier controls."
                    )
                else:
                    why_it_matters = (
                        f"This observation shows a failed barrier ({barrier_label}: "
                        f"{state_label}) during {act_names} work. Recurrence is not "
                        f"established with only {len(group)} observation; monitor "
                        f"for further reports."
                    )
            else:
                act_str = (
                    self.ontology.label("activity", activities[0])
                    if activities else "routine work"
                )
                if recurring:
                    why_it_matters = (
                        f"{len(group)} observations indicate a recurring barrier "
                        f"vulnerability in {barrier_label} during {act_str}."
                    )
                else:
                    why_it_matters = (
                        f"A single observation indicates an unverified barrier state "
                        f"({barrier_label}: {state_label}) during {act_str}. "
                        f"Recurrence is not yet established; monitor for additional "
                        f"reports of the same mechanism."
                    )
        elif family_type == "controlled":
            why_it_matters = (
                f"{len(group)} observation(s) confirm positive verification of "
                f"{self.ontology.label('barrier', barrier)} prior to work on energized systems. "
                f"Risk controls functioning as designed."
            )
        else:
            why_it_matters = (
                "Critical safety mechanism cannot be established from the available narrative. "
                "Requires HSE specialist review to classify required barrier controls."
            )

        attention = compute_attention(group)

        sif_high_count = sum(
            1 for e in events if e.sif.classification == "high"
        )

        grouping_evidence = self._grouping_evidence(events)

        parts = [
            f"{len(group)} observation(s)"
            f"{' — recurring precursor mechanism' if recurring else ' — single observation; recurrence not established'}.",
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
        else:
            parts.append("Exposure: Unknown / unconfirmed across member reports.")
        description = " ".join(parts)

        return PrecursorFamily(
            id=family_id,
            name=name,
            family_type=family_type,
            description=description,
            observation_ids=[o.id for o in group],
            common_barrier=barrier,
            common_barrier_state=state,
            common_energy=energy,
            common_exposure=exposure,
            core_mechanism=core_mechanism,
            context=context,
            recurrence=recurrence,
            why_it_matters=why_it_matters,
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
        CORE_FIELDS = {"energy", "barrier", "barrier_state", "exposure"}
        for dimension, attr in GROUPING_DIMENSIONS:
            category = "core_mechanism" if dimension in CORE_FIELDS else "context"
            known: list[str] = []
            for e in events:
                value = getattr(e, attr)
                if value and value != UNKNOWN_CODE:
                    known.append(value)
            if not known:
                out.append(GroupingEvidence(
                    dimension=dimension,
                    category=category,
                    value="",
                    status="unknown",
                    coverage=0.0,
                    note="Unknown / not stated across member reports",
                ))
                continue
            counts = Counter(known)
            dominant, count = counts.most_common(1)[0]
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
                category=category,
                value=dominant,
                status=status,
                coverage=coverage,
                note=(
                    f"Invariant match: {label} across all {n} observation(s)"
                    if status == "same" else
                    f"{label} dominant ({count}/{n}), {n - count} differ. "
                    f"Differing {dimension} allowed: mechanism (barrier/energy) is invariant across operations."
                    if dimension in ("activity", "location", "task_phase") else
                    f"{label} dominant ({count}/{n}), {n - count} differ"
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

    def _dominant(self, events, field: str, require_majority: bool = False) -> str:
        counter: dict[str, int] = {}
        for e in events:
            value = getattr(e, field)
            if value and value != UNKNOWN_CODE:
                counter[value] = counter.get(value, 0) + 1
        if not counter:
            return UNKNOWN_CODE
        top_val, top_cnt = max(
            counter.items(),
            key=lambda kv: (kv[1], -_code_len(kv[0])),
        )
        if require_majority and top_cnt < (len(events) + 1) // 2:
            return UNKNOWN_CODE
        return top_val

    def _name(self, barrier: str, state: str) -> str:
        by_barrier = self.templates.get(barrier, {})
        if isinstance(by_barrier, dict):
            return by_barrier.get(state, self.default)
        return self.default


def _code_len(code: str) -> int:
    return len(code)