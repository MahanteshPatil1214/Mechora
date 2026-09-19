"""Document upload endpoints: extract text, optionally analyze it.

Extraction logic lives entirely in ``app.services.document_extractor``; these
routes only validate the upload envelope (extension + magic bytes + size +
character budget) and hand normalized text to the existing single analysis
path (``run_analysis_and_save``).
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.routes.analyze import run_analysis_and_save
from app.config import get_settings
from app.schemas.api import AnalyzeResponse
from app.services.document_extractor.extractor import (
    EmptyDocumentError,
    ExtractedDocument,
    UnsupportedDocumentTypeError,
    extract_text,
)

router = APIRouter(tags=["documents"])


def _validated_extraction(file: UploadFile) -> ExtractedDocument:
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
        return extract_text(file.filename or "", data)
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _enforce_character_budget(text: str) -> None:
    limit = get_settings().max_document_characters
    if len(text) > limit:
        raise HTTPException(
            status_code=422,
            detail=(
                f"extracted text is {len(text)} characters, exceeding the "
                f"{limit}-character analysis limit; upload a shorter report"
            ),
        )
    if len(text) < 8:
        raise HTTPException(
            status_code=422,
            detail="document contains too little text to analyze (minimum 8 characters)",
        )


@router.post("/documents/extract")
def extract_document(file: UploadFile = File(...)) -> dict:
    """Extract plain text from an uploaded PDF/DOCX/TXT report."""
    extracted = _validated_extraction(file)
    _enforce_character_budget(extracted.text)
    return {
        "filename": extracted.filename,
        "file_type": extracted.file_type,
        "text": extracted.text,
        "character_count": extracted.character_count,
    }


@router.post("/documents/analyze", response_model=AnalyzeResponse)
def analyze_document(
    file: UploadFile = File(...),
    report_id: str | None = None,
    provider: str | None = None,
) -> AnalyzeResponse:
    """Extract then analyze an uploaded report through the existing pipeline."""
    extracted = _validated_extraction(file)
    _enforce_character_budget(extracted.text)
    default_id = f"DOC-{extracted.file_type.upper()}"
    return run_analysis_and_save(report_id or default_id, extracted.text, provider)