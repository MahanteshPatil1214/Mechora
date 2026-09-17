"""Connectivity clustering of structural signatures into precursor families."""

from __future__ import annotations

from app.models.safety_event import PrecursorSignature
from app.services.precursor.similarity import StructuralSimilarity


def connected_groups(
    signatures: list[PrecursorSignature],
    threshold: float,
    similarity: StructuralSimilarity | None = None,
) -> list[list[int]]:
    """Return groups of indices whose pairwise structure exceeds threshold.

    Uses single-linkage connectivity: index i and j belong to the same family
    if they are linked via a chain of matching observations. Matches the PRD
    intent of grouping "different equipment, different wording, same failed
    barrier" while the verified-vs-failure hard rule blocks spurious merges.
    """
    similarity = similarity or StructuralSimilarity()
    n = len(signatures)
    adj: list[list[int]] = [[] for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            result = similarity.score(signatures[i], signatures[j])
            if result["similarity"] >= threshold:
                adj[i].append(j)
                adj[j].append(i)

    seen = [False] * n
    groups: list[list[int]] = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        group: list[int] = []
        while stack:
            cur = stack.pop()
            group.append(cur)
            for nb in adj[cur]:
                if not seen[nb]:
                    seen[nb] = True
                    stack.append(nb)
        groups.append(group)
    return groups