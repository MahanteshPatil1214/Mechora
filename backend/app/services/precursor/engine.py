"""Precursor engine: signature -> similarity -> clustering -> families.

This is the primary differentiating component. Structural similarity is the
primary mechanism; embeddings are an optional supporting signal only.
"""

from __future__ import annotations

from app.config import Settings
from app.models.safety_event import Observation, PrecursorFamily
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

        # Embedding support (optional): we intentionally keep this a no-op
        # unless an embedding model is configured. Structural similarity is
        # primary by design (PRD section 14).
        groups = connected_groups(
            signatures, threshold=self.threshold, similarity=self.similarity
        )

        grouped_obs = [[ordered[i] for i in g] for g in groups]
        # Sort groups so that smaller (single) families come last.
        grouped_obs.sort(key=lambda g: -len(g))

        return self.family_builder.build(grouped_obs, family_index=start_family_index)