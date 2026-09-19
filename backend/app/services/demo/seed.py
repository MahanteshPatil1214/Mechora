"""Curated SIH demo dataset: deterministic reset + load through the pipeline.

The curated dataset lives in ONE place (data/demo/demo_reports_7.txt) and is
loaded through the exact document path used for uploaded files: the segmenter
splits the file into 7 report segments plus an excluded NON-REPORT block, and
every report segment is analysed independently via ``AnalysisPipeline`` with
document/report-segment/segment-index traceability ids mirroring the document
analyze route.

Reset semantics: clearing observations and precursor families is an EXPLICIT
operator action (``scripts/seed_demo.py``). Production data is never deleted
automatically.
"""

from __future__ import annotations

from pathlib import Path

from app.database import repos
from app.database.engine import backend_name, dispose, init_db
from app.database.tables import ObservationRow, PrecursorFamilyRow
from app.services.document_segmentation.segmenter import ReportSegmenter
from app.services.pipeline import AnalysisPipeline

PARENT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DEMO_DATASET_PATH = PARENT_DIR / "data" / "demo" / "demo_reports_7.txt"

DOCUMENT_ID = "DEMO-CURATED"
EXTRACTION_PROVIDER = "rules"


def curated_documents(segmenter: ReportSegmenter | None = None) -> list[dict]:
    """Segment the curated demo file into its report documents.

    Returns one dict per report segment with document/report-segment ids,
    segment index, heading and narrative text. NON-REPORT blocks never appear.
    """
    text = DEMO_DATASET_PATH.read_text(encoding="utf-8")
    segmenter = segmenter or ReportSegmenter()
    documents = []
    for index, seg in enumerate(segmenter.reports(text), start=1):
        seg_id = f"{DOCUMENT_ID}-SEG{index}"[:40]
        documents.append({
            "index": seg.index,
            "document_id": DOCUMENT_ID,
            "report_segment_id": seg_id,
            "report_id": seg_id,
            "heading": seg.heading,
            "text": seg.text,
            "character_count": seg.character_count,
        })
    return documents


def seed_curated_demo(settings=None, ontology=None,
                      provider: str | None = None) -> dict:
    """Reset and load the curated demo dataset.

    Deterministic: extraction provider defaults to ``rules`` so families,
    evidence spans and ids are stable across seeding cycles. Returns a summary
    dict (observation count, family breakdown) for CLI / test assertions.
    """
    from sqlalchemy import delete

    from app.database.engine import get_session
    from app.services.normalization.ontology import get_ontology

    dispose()
    init_db()
    with get_session() as s:
        s.execute(delete(PrecursorFamilyRow))
        s.execute(delete(ObservationRow))
        s.commit()

    pipeline = AnalysisPipeline(ontology or get_ontology(), settings)
    documents = curated_documents()
    observations = []
    for doc in documents:
        obs = pipeline.to_observation(
            doc["report_id"],
            doc["text"],
            provider=provider or EXTRACTION_PROVIDER,
            document_id=doc["document_id"],
            report_segment_id=doc["report_segment_id"],
            segment_index=doc["index"],
        )
        obs.id = repos.new_observation_id(doc["report_id"])
        observations.append(obs)

    repos.bulk_create_observations(observations)
    return {
        "observations_seeded": len(observations),
        "documents": documents,
        "backend": backend_name(),
    }


def reset_demo() -> None:
    """Explicit operator action: clear observations and precursor families."""
    from sqlalchemy import delete

    from app.database.engine import get_session

    dispose()
    init_db()
    with get_session() as s:
        s.execute(delete(PrecursorFamilyRow))
        s.execute(delete(ObservationRow))
        s.commit()


def demo_summary() -> dict:
    """Deterministic post-seed counts for the CLI and demo acceptance."""
    summary = repos.dashboard_summary()
    families = [
        {
            "id": f.id,
            "name": f.name,
            "n": len(f.observation_ids),
            "recurring": f.recurring,
            "family_type": f.family_type,
            "attention_signal": f.attention_signal,
        }
        for f in repos.list_families(limit=100, include_controls=True)
    ]
    return {
        "observations": repos.count_observations(),
        "precursor_families": summary["precursor_families"],
        "recurring_families": summary["recurring_precursor_families"],
        "families": families,
    }