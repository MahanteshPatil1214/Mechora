"""Narrative analysis endpoint (extract + validate + persist)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.database import repos
from app.schemas.api import AnalyzeRequest, AnalyzeResponse
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

router = APIRouter(tags=["analyze"])

_pipeline: AnalysisPipeline | None = None


def _get_pipeline() -> AnalysisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline(get_ontology(), get_settings())
    return _pipeline


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    report_id = (req.report_id or "REPORT-UNASSIGNED").strip()[:128]
    pipeline = _get_pipeline()
    try:
        result = pipeline.analyze(report_id, req.narrative, provider=req.provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}") from exc

    obs = pipeline.to_observation(
        report_id, req.narrative, provider=result.provider
    )
    saved = repos.create_observation(obs)
    return AnalyzeResponse(
        id=saved.id,
        report_id=saved.report_id,
        provider=saved.provider,
        warnings=result.warnings,
        event=saved.event.model_dump(),
        precursor_family_id=saved.precursor_family_id,
    )