"""Regression harness: the frozen 216-record evaluation set must keep
acceptance-level performance under the deterministic rule pipeline.
"""

from __future__ import annotations

import json

from app.config import get_settings
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

FIELDS = [
    "activity", "task_phase", "energy", "barrier", "barrier_state",
    "exposure", "potential_consequence",
]

# PRD acceptance thresholds (kept intentionally strict).
THRESHOLDS = {
    "schema_valid": 1.0,
    "activity": 0.95,
    "task_phase": 0.90,
    "energy": 0.90,
    "barrier": 0.92,
    "barrier_state": 0.95,
    "exposure": 0.92,
    "potential_consequence": 0.90,
    "isolation_verified_vs_not_verified": 0.98,
    "hard_negative_no_false_negation": 0.95,
}


def _load_records():
    doc = json.loads(get_settings().eval_set_path.read_text(encoding="utf-8"))
    return doc["records"]


def _run_all():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    hits = {f: 0 for f in FIELDS}
    totals = {f: 0 for f in FIELDS}
    neg_ok = neg_n = 0
    hard_ok = hard_n = 0
    schema_ok = 0
    n = len(_load_records())
    for rec in _load_records():
        event = pipeline.analyze(rec["report_id"], rec["narrative"],
                                 provider="rules").event
        schema_ok += 1
        gt = rec["ground_truth"]
        for f in FIELDS:
            totals[f] += 1
            hits[f] += getattr(event, f) == gt.get(f, "unknown")
        if rec["category"] == "negation":
            neg_n += 1
            g = gt.get("barrier_state")
            p = event.barrier_state
            if p == g and g in ("verified", "not_verified"):
                neg_ok += 1
        if rec["category"] == "hard_negative":
            hard_n += 1
            if gt.get("barrier_state") == "verified" and \
                    event.barrier_state == "verified":
                hard_ok += 1
    return {
        "schema_valid": schema_ok / n,
        "field": {f: hits[f] / totals[f] for f in FIELDS},
        "negation": neg_ok / neg_n if neg_n else 1.0,
        "hard_negative": hard_ok / hard_n if hard_n else 1.0,
        "n": n,
    }


def test_eval_set_volume():
    assert len(_load_records()) >= 200


def test_acceptance_thresholds_hold():
    metrics = _run_all()
    assert metrics["schema_valid"] >= THRESHOLDS["schema_valid"]
    for metric, threshold in THRESHOLDS.items():
        if metric in metrics["field"]:
            assert metrics["field"][metric] >= threshold, metric
        elif metric in metrics:
            assert metrics[metric] >= threshold, metric
    assert metrics["n"] >= 200