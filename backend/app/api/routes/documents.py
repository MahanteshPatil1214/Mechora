"""Document upload endpoints: extract + segment, optionally analyze.

Pipeline stage: Extraction -> Document Segmentation -> Evidence-grounded
analysis. Extraction and segmentation logic live in their services; these
routes only validate the upload envelope (extension + magic bytes + size +
character budget), segment the extracted text, and hand EACH report segment to
the existing single analysis path (``run_analysis_and_save``) independently.

Non-report blocks (headers, "Expected Test Signals" instructional blocks,
metadata ``Label:`` lines, page furniture) are excluded from analysis, evidence
and traceability: they are never sent to the pipeline.
"""

from __future__ import annotations

import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.api.routes.analyze import run_analysis_and_save
from app.config import get_settings
from app.schemas.api import (
    AnalyzeResponse,
    DocumentAnalysisResponse,
    ExtractionResponse,
    SegmentAnalysis,
)
from app.security.auth import require_auth
from app.services.document_extractor.extractor import (
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
    extract_text,
)
from app.services.document_segmentation.segmenter import (
    MIN_REPORT_CHARACTERS,
    ReportSegmenter,
)

router = APIRouter(tags=["documents"], dependencies=[Depends(require_auth)])

_ALLOWED_PROVIDERS = ("rules", "llm", "auto")


def _validated_extraction_file(file: UploadFile) -> str:
    settings = get_settings()
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"uploaded file exceeds the {settings.max_upload_bytes // (1024 * 1024)} "
                "MB size limit"
            ),
        )
    try:
        extracted = extract_text(file.filename or "", data)
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    limit = settings.max_document_characters
    if len(extracted.text) < 8:
        raise HTTPException(
            status_code=422,
            detail="document contains too little text to analyze (minimum 8 characters)",
        )
    if len(extracted.text) > limit:
        raise HTTPException(
            status_code=422,
            detail=(
                f"extracted text is {len(extracted.text)} characters, exceeding the "
                f"{limit}-character analysis limit; upload a shorter report"
            ),
        )
    return extracted.text


def _document_id(filename: str, file_type: str, prefix: str | None) -> str:
    """Deterministic document id (per report segment: ``<doc>-SEG<n>``)."""
    base = filename or ""
    if "." in base:
        base = base.rsplit(".", 1)[0]
    stem = re.sub(r"[^A-Z0-9]+", "-", (base or file_type or "DOC").upper()).strip("-")
    stem = (stem or file_type or "DOC")[:40].strip("-")
    if prefix:
        pref = re.sub(r"[^A-Z0-9]+", "-", (prefix or "").upper()).strip("-")
        if pref:
            stem = pref[:40].strip("-")
    return f"DOC-{stem}"


def _segment_id(doc_id: str, segment_index: int) -> str:
    return f"{doc_id}-SEG{segment_index}"[:40]


@router.post("/documents/extract", response_model=ExtractionResponse)
def extract_document(file: UploadFile = File(...)) -> ExtractionResponse:
    """Extract, then SEGMENT an uploaded PDF/DOCX/TXT report.

    Returns the full plain text plus classified segments; ``report`` segments
    are the analysisable observations, ``non_report`` segments are excluded.
    """
    text = _validated_extraction_file(file)
    file_type = (file.filename or "").rsplit(".", 1)[-1].lower() or "txt"
    segments = ReportSegmenter().segment(text)
    reports = [s for s in segments if s.kind == "report"]
    return ExtractionResponse(
        filename=file.filename or "",
        file_type=file_type,
        text=text,
        character_count=len(text),
        report_count=len(reports),
        segments=[s.to_dict() for s in segments],
        warnings=_extract_warnings(segments),
    )


def _extract_warnings(segments) -> list[str]:
    warnings: list[str] = []
    for seg in segments:
        if seg.kind == "report" and seg.character_count < MIN_REPORT_CHARACTERS:
            warnings.append(
                f"report segment {seg.index} is too short to analyze "
                f"({seg.character_count} chars); skipped"
            )
    if not any(s.kind == "report" for s in segments):
        warnings.append("no report segments found; document may be non-report material")
    return warnings


@router.post("/documents/analyze", response_model=DocumentAnalysisResponse)
def analyze_document(
    file: UploadFile = File(...),
    report_id: str | None = None,
    provider: str | None = None,
    report_type: str = Form("unknown"),
) -> DocumentAnalysisResponse:
    """Extract, segment, then analyze EACH report independently.

    Each report segment gets its own observation (``report_id=<doc>-SEG<n>``),
    so multi-observation documents never merge two events into one analysis and
    non-report material never contaminates evidence. ``report_type`` is
    reporter-selected metadata applied to every segment of the document.
    """
    if not isinstance(report_type, str):  # direct-call tolerance (non-HTTP)
        report_type = "unknown"
    if provider not in (None, *_ALLOWED_PROVIDERS):
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(_ALLOWED_PROVIDERS)}",
        )
    text = _validated_extraction_file(file)
    file_type = (file.filename or "").rsplit(".", 1)[-1].lower() or "txt"
    doc_id = _document_id(file.filename or "", file_type, report_id)
    reports = ReportSegmenter().reports(text)

    analyses: list[SegmentAnalysis] = []
    for seg in reports:
        seg_id = _segment_id(doc_id, seg.index)
        try:
            result: AnalyzeResponse = run_analysis_and_save(
                seg_id,
                seg.text,
                provider,
                document_id=doc_id,
                report_segment_id=seg_id,
                segment_index=seg.index,
                report_type=report_type,
            )
            analyses.append(SegmentAnalysis(
                report_segment_id=seg_id,
                segment_index=seg.index,
                heading=seg.heading,
                analysis=result,
            ))
        except HTTPException as exc:
            analyses.append(SegmentAnalysis(
                report_segment_id=seg_id,
                segment_index=seg.index,
                heading=seg.heading,
                error=str(exc.detail),
            ))

    return DocumentAnalysisResponse(
        document_id=doc_id,
        report_count=len(reports),
        analyses=analyses,
        observations_created=sum(
            1 for a in analyses if a.analysis is not None
        ),
        warnings=_extract_warnings(reports),
    )