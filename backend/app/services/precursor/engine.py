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
        from app.services.precursor.clustering import _is_critical_known

        ordered = sorted(observations, key=lambda o: o.created_at)
        if not ordered:
            return [], {}

        confident_obs: list[Observation] = []
        assignment: dict[str, str] = {}

        for o in ordered:
            sig = build_signature(o.event)
            if o.event.needs_review or not _is_critical_known(sig):
                assignment[o.id] = "UNASSIGNED / PENDING REVIEW"
            else:
                confident_obs.append(o)

        if not confident_obs:
            return [], assignment

        signatures = [build_signature(o.event) for o in confident_obs]
        sig_by_id = {confident_obs[i].id: signatures[i] for i in range(len(confident_obs))}

        # Embedding support (optional): we intentionally keep this a no-op
        # unless an embedding model is configured. Structural similarity is
        # primary by design (PRD section 14).
        groups = connected_groups(
            signatures, threshold=self.threshold, similarity=self.similarity
        )

        grouped_obs = [[confident_obs[i] for i in g] for g in groups]
        # Sort groups so that smaller (single) families come last.
        grouped_obs.sort(key=lambda g: -len(g))

        families, conf_assignment = self.family_builder.build(
            grouped_obs,
            family_index=start_family_index,
            recurring_threshold=self.recurring_threshold,
        )
        assignment.update(conf_assignment)
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
        fam_by_id = {f.id: f for f in families}
        for fam in families:
            candidates: list[tuple[float, str, list[str], list[dict[str, str]]]] = []
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
                best_details: list[dict] = []
                for sa in mine:
                    for sb in theirs:
                        res = self.similarity.score(sa, sb)
                        s = res.get("dimension_similarity", res["similarity"])
                        if s > best_rank[0]:
                            best_rank = (s, s)
                            best_dims = [
                                d["field"] for d in res["details"]
                                if d.get("match") == 0
                                and d.get("field") != "hard_rule"
                            ]
                            best_details = res.get("details", [])
                if best_rank[0] >= self.exclusion_floor:
                    # Build field-level comparisons with real values
                    comparisons: list[dict[str, str]] = []
                    for d in best_details:
                        fld = d.get("field")
                        if not fld or fld == "hard_rule":
                            continue
                        va = str(d.get("a", "unknown"))
                        vb = str(d.get("b", "unknown"))
                        lbl_a = (
                            self.ontology.label(fld, va)
                            if fld in self.ontology.CONCEPT_FILE_KEYS
                            else va.replace("_", " ").title()
                        )
                        lbl_b = (
                            self.ontology.label(fld, vb)
                            if fld in self.ontology.CONCEPT_FILE_KEYS
                            else vb.replace("_", " ").title()
                        )
                        is_match = d.get("match", 0) == 1
                        comparisons.append({
                            "dimension": fld,
                            "this_value": va,
                            "this_label": lbl_a,
                            "other_value": vb,
                            "other_label": lbl_b,
                            "match": "same" if is_match else "differs",
                        })
                    candidates.append((best_rank[0], other.id, best_dims, comparisons))
            candidates.sort(key=lambda c: (-c[0], c[1]))
            for sim, other_id, dims, comps in candidates[:3]:
                other_fam = fam_by_id.get(other_id)
                other_name = other_fam.name if other_fam else other_id
                
                # Identify which critical difference caused mechanism separation
                diff_map = {c["dimension"]: c for c in comps if c.get("match") == "differs"}
                if "barrier" in diff_map:
                    c = diff_map["barrier"]
                    separation_reason = f"Barrier: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM"
                elif "barrier_state" in diff_map:
                    c = diff_map["barrier_state"]
                    vals = {c.get("this_value"), c.get("other_value")}
                    if vals == {"not_verified", "failed"}:
                        separation_reason = (
                            f"Barrier State: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM "
                            f"(Procedural Verification Omission vs. Physical Hardware Failure)"
                        )
                    elif "verified" in vals:
                        separation_reason = (
                            f"Barrier State: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM "
                            f"(Verified Positive Check vs. Barrier Degradation)"
                        )
                    else:
                        separation_reason = f"Barrier State: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM"
                elif "energy" in diff_map:
                    c = diff_map["energy"]
                    separation_reason = f"Hazard/Energy: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM"
                elif "exposure" in diff_map:
                    c = diff_map["exposure"]
                    separation_reason = f"Exposure: {c['this_label']} != {c['other_label']} -> DIFFERENT MECHANISM"
                elif diff_map:
                    first_c = list(diff_map.values())[0]
                    separation_reason = f"{first_c['dimension'].replace('_', ' ').title()}: {first_c['this_label']} != {first_c['other_label']} -> DIFFERENT MECHANISM"
                else:
                    separation_reason = "DIFFERENT MECHANISM"

                fam.exclusions.append(ExclusionEntry(
                    other_family_id=other_id,
                    other_family_name=other_name,
                    similarity=round(sim, 6),
                    differing_dimensions=dims[:10],
                    dimension_comparisons=comps,
                    basis=separation_reason,
                ))