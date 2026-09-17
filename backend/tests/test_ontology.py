"""Ontology integrity tests (regression for the aux-loading bug)."""

from __future__ import annotations

import json

from app.config import get_settings
from app.services.normalization.ontology import get_ontology


def test_aux_tables_are_non_empty():
    """Aux ontology tables (negation, lsr, sif, family) must load."""
    onto = get_ontology()
    assert onto.negation_cues().get("states", {})
    assert onto.lsr_table().get("barrier_to_rule", {})
    assert onto.lsr_table().get("energy_to_rule", {})
    assert onto.family_templates() is not None
    assert onto.sif_rules() is not None
    states = onto.negation_cues()["states"]
    assert "not_verified" in states
    assert states["not_verified"]["priority"] > states["failed"]["priority"]


def test_every_concept_has_synonyms():
    onto = get_ontology()
    for category in ("activity", "energy", "barrier", "exposure",
                     "consequence", "location"):
        for concept in onto.concepts(category):
            assert concept.synonyms, (category, concept.code)


def test_eval_set_uses_only_canonical_codes():
    from app.models.safety_event import (
        ACTIVITY_CODES, BARRIER_CODES, BARRIER_STATE_CODES, ENERGY_CODES,
        EXPOSURE_CODES,
    )

    valid_activity = set(_flat(ACTIVITY_CODES))
    valid_energy = set(_flat(ENERGY_CODES))
    valid_barrier = set(_flat(BARRIER_CODES))
    valid_state = set(_flat(BARRIER_STATE_CODES))
    valid_exposure = set(_flat(EXPOSURE_CODES))

    doc = json.loads(get_settings().eval_set_path.read_text(encoding="utf-8"))
    assert len(doc["records"]) >= 200
    for rec in doc["records"]:
        gt = rec["ground_truth"]
        assert rec["report_id"].startswith("EVAL-")
        assert gt["activity"] in valid_activity, rec["report_id"]
        assert gt["energy"] in valid_energy, rec["report_id"]
        assert gt["barrier"] in valid_barrier, rec["report_id"]
        assert gt["barrier_state"] in valid_state, rec["report_id"]
        assert gt["exposure"] in valid_exposure, rec["report_id"]


def _flat(literal) -> list[str]:
    args = getattr(literal, "__args__", None)
    return [a for a in args if isinstance(a, str)] if args else [literal]