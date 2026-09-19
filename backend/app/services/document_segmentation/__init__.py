"""MECHORA document-segmentation service.

Structural-only layer: splits one extracted document into independent report
segments (each observation is analyzed and persisted separately) and drops
non-report material (headings, metadata ``Label:`` lines, "Expected Test
Signals" instructional blocks, page headers/footers) from analysis, evidence
and traceability. No NLP, no inference.
"""