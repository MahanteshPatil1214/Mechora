"""Connectivity clustering of structural signatures into precursor families."""

from __future__ import annotations

from app.models.safety_event import PrecursorSignature
from app.services.precursor.similarity import StructuralSimilarity


MISSING = {"", "unknown", "needs_review", "none_identified"}


def _is_known(val: str) -> bool:
    return bool(val) and val not in MISSING


def _is_critical_known(sig: PrecursorSignature) -> bool:
    b = getattr(sig, "barrier", "")
    s = getattr(sig, "barrier_state", "")
    e = getattr(sig, "energy", "")
    ex = getattr(sig, "exposure", "")
    if not _is_known(b) or not _is_known(s) or not _is_known(e):
        return False
    if s != "verified" and not _is_known(ex):
        return False
    return True


def connected_groups(
    signatures: list[PrecursorSignature],
    threshold: float,
    similarity: StructuralSimilarity | None = None,
) -> list[list[int]]:
    """Return groups of indices whose pairwise structure exceeds threshold.

    Uses single-linkage connectivity: index i and j belong to the same family
    if they are linked via a chain of matching observations. Matches the PRD
    intent of grouping "different equipment, different wording, same failed
    barrier" while ensuring different barriers and different barrier states
    remain separate.
    """
    similarity = similarity or StructuralSimilarity()
    n = len(signatures)
    adj: list[list[int]] = [[] for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            sig_a = signatures[i]
            sig_b = signatures[j]
            ba, bb = getattr(sig_a, "barrier", ""), getattr(sig_b, "barrier", "")
            sa, sb = getattr(sig_a, "barrier_state", ""), getattr(sig_b, "barrier_state", "")
            ea, eb = getattr(sig_a, "energy", ""), getattr(sig_b, "energy", "")

            # Structural Precursor Principle:
            # 1. Missing critical fields cannot group into a confident precursor family
            if not _is_critical_known(sig_a) or not _is_critical_known(sig_b):
                continue

            # 2. Different barriers must remain separate
            if ba != bb:
                continue

            # 3. Different barrier states must remain separate
            if sa != sb:
                continue

            # 4. Different energy mechanisms must remain separate
            if ea != eb:
                continue

            result = similarity.score(sig_a, sig_b)
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