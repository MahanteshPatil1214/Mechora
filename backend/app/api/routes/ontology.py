"""Ontology reference + evaluation metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.database import repos
from app.schemas.api import EvaluationOut, OntologyCategory, OntologyConcept
from app.security.auth import require_auth
from app.services.normalization.ontology import get_ontology

router = APIRouter(tags=["ontology", "evaluation"], dependencies=[Depends(require_auth)])

CATEGORIES = [
    "activity", "energy", "barrier", "exposure", "consequence", "location",
]


@router.get("/ontology", response_model=list[OntologyCategory])
def ontology_reference() -> list[OntologyCategory]:
    onto = get_ontology()
    out: list[OntologyCategory] = []
    for category in CATEGORIES:
        concepts = onto.concepts(category)
        if not concepts:
            continue
        out.append(
            OntologyCategory(
                category=category,
                concepts=[
                    OntologyConcept(code=c.code, synonyms=c.synonyms)
                    for c in concepts
                ],
            )
        )
    return out


@router.get("/evaluation/latest", response_model=EvaluationOut)
def latest_evaluation() -> EvaluationOut:
    row = repos.latest_evaluation()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="no evaluation stored yet; run scripts/run_evaluation.py",
        )
    return EvaluationOut(**row)