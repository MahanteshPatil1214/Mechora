"""Precursor engine: signature -> similarity -> clustering -> families.

This is the primary differentiating component. Structural similarity is the
primary mechanism; embeddings are an optional supporting signal only.
Families carry WHY GROUPED? evidence (per-dimension agreement) and WHY NOT
GROUPED? exclusions (structurally-similar families kept separate).
"""

from __future__ import annotations

from app.config import Settings
from app.models.safety_event import (  # noqa: TC001
    ExclusionEntry,
    Observation,
    PrecursorFamily,
)
from app.services.normalization.ontology import Ontology
from app.services.precursor.clustering import connected_groups
from app.services.precursor.family import FamilyBuilder
from app.services.precursor.similarity import StructuralSimilarity, build_signature


class PrecursorEngine:
    def __init__(self, ontology: Ontology, settings: Settings | None = None) -> None:
        self.ontology = ontology
        self.settings = settings
        threshold = settings.family_assign_threshold if settings else 0.65
        self.threshold = threshold
        exclusion_floor = (
            settings.family_exclusion_floor if settings else 0.35
        )
        self.exclusion_floor = exclusion_floor
        recurring_threshold = (
            settings.recurring_min_observations if settings else 2
        )
        self.recurring_threshold = recurring_threshold
        self.similarity = StructuralSimilarity()
        self.family_builder = FamilyBuilder(ontology)

    def run(self, observations: list[Observation],
            start_family_index: int = 0) -> tuple[list[PrecursorFamily], dict[str, str]]:
        """Compute families for observations in order.

        Returns (families, obs_id -> family_id assignment).
        """
        ordered = sorted(observations, key=lambda o: o.created_at)
        if not ordered:
            return [], {}

        signatures = [build_signature(o.event) for o in ordered]
        sig_by_id = {ordered[i].id: signatures[i] for i in range(len(ordered))}

        # Embedding support (optional): we intentionally keep this a no-op
        # unless an embedding model is configured. Structural similarity is
        # primary by design (PRD section 14).
        groups = connected_groups(
            signatures, threshold=self.threshold, similarity=self.similarity
        )

        grouped_obs = [[ordered[i] for i in g] for g in groups]
        # Sort groups so that smaller (single) families come last.
        grouped_obs.sort(key=lambda g: -len(g))

        families, assignment = self.family_builder.build(
            grouped_obs,
            family_index=start_family_index,
            recurring_threshold=self.recurring_threshold,
        )
        self._attach_exclusions(families, grouped_obs, sig_by_id)
        return families, assignment

    # ------------------------------------------------------------- internal

    def _attach_exclusions(self, families: list[PrecursorFamily],
                           grouped_obs: list[list[Observation]],
                           sig_by_id: dict[str, object]) -> None:
        """WHY NOT GROUPED? For each family, find the nearest structurally
        similar family (>= floor) that was NOT merged, using the actual
        per-observation similarity scores and reporting the differing
        dimensions on the closest pair."""
        member_sigs = {
            fam.id: [sig_by_id[oid] for oid in fam.observation_ids
                     if oid in sig_by_id]
            for fam in families
        }
        for fam in families:
            candidates: list[tuple[float, str, list[str]]] = []
            mine = member_sigs.get(fam.id, [])
            if not mine:
                continue
            for other in families:
                if other.id == fam.id:
                    continue
                theirs = member_sigs.get(other.id, [])
                if not theirs:
                    continue
                best_rank = (-1.0, "")
                best_dims: list[str] = []
                for sa in mine:
                    for sb in theirs:
                        res = self.similarity.score(sa, sb)
                        s = res["similarity"]
                        if s > best_rank[0]:
                            best_rank = (s, s)
                            best_dims = [
                                d["field"] for d in res["details"]
                                if d.get("match") == 0
                                and d.get("field") != "hard_rule"
                            ]
                if best_rank[0] >= self.exclusion_floor:
                    candidates.append((best_rank[0], other.id, best_dims))
            candidates.sort(key=lambda c: (-c[0], c[1]))
            for sim, other_id, dims in candidates[:3]:
                fam.exclusions.append(ExclusionEntry(
                    other_family_id=other_id,
                    similarity=round(sim, 6),
                    differing_dimensions=dims[:10],
                    basis=(
                        f"Similar structure ({sim:.2f}) but kept separate: "
                        + (", ".join(dims[:5]) if dims else "no shared value")
                    ),
                ))