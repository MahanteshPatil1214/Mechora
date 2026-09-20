"""Narrative analysis endpoint (extract + validate + persist).

The single analysis path: every route that analyses text (manual JSON input or
an uploaded document) funnels through :func:`run_analysis_and_save`, which runs
:class:`AnalysisPipeline` and persists one observation.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.database import repos
from app.schemas.api import AnalyzeRequest, AnalyzeResponse
from app.services.pipeline import get_pipeline

router = APIRouter(tags=["analyze"])


def run_analysis_and_save(
    report_id: str | None,
    narrative: str,
    provider: str | None = None,
    document_id: str = "",
    report_segment_id: str = "",
    segment_index: int | None = None,
    report_type: str | None = None,
) -> AnalyzeResponse:
    raw_id = (report_id or "REPORT-UNASSIGNED").strip()[:100]
    report_id = (
        f"{raw_id}-{uuid.uuid4().hex[:6]}"
        if (not raw_id or raw_id == "REPORT-UNASSIGNED")
        else raw_id
    )
    pipeline = get_pipeline(get_settings())
    try:
        result = pipeline.analyze(report_id, narrative, provider=provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}") from exc

    obs = pipeline.to_observation(
        report_id,
        narrative,
        provider=provider,
        document_id=document_id,
        report_segment_id=report_segment_id,
        segment_index=segment_index,
        report_type=report_type,
    )
    saved = repos.create_observation(obs)

    return AnalyzeResponse(
        id=saved.id,
        report_id=saved.report_id,
        provider=saved.provider,
        resolved_provider=saved.provider,
        requested_provider=saved.requested_provider,
        fallback_used=saved.fallback_used,
        fallback_reason=saved.fallback_reason,
        warnings=result.warnings,
        event=saved.event.model_dump(),
        precursor_family_id=saved.precursor_family_id,
        document_id=saved.document_id,
        report_segment_id=saved.report_segment_id,
        segment_index=saved.segment_index,
        report_type=saved.report_type,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    return run_analysis_and_save(
        req.report_id, req.narrative, req.provider, report_type=req.report_type
    )