"""Run the frozen evaluation set through the MECHORA rule pipeline.

Reads data/evaluation/eval_set.json, scores each record against the ground
truth, applies the PRD critical-suite assertions, writes the detail +
summary to data/evaluation/results/ and prints a report.

This uses the deterministic rule extractor (offline, reproducible). No
fabricated metrics: every number here comes from this run.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.services.normalization.ontology import get_ontology  # noqa: E402
from app.services.pipeline import AnalysisPipeline  # noqa: E402

FIELDS = [
    "activity",
    "task_phase",
    "energy",
    "barrier",
    "barrier_state",
    "exposure",
    "potential_consequence",
    "location",
]

SIF_CLASSES = ["high", "medium", "low", "needs_review"]


def _norm(v: str) -> str:
    return str(v or "").strip()


def gt_field(rec: dict, key: str) -> str:
    val = rec["ground_truth"].get(key)
    return _norm(val) if val is not None else "unknown"


def pred_field(event, key: str) -> str:
    if key == "location":
        return _norm(event.location) or "unknown"
    if key == "potential_consequence":
        return _norm(event.potential_consequence) or "unknown"
    return _norm(getattr(event, key)) or "unknown"


def predicted_family_tag(event) -> str:
    if not event.barrier or event.barrier == "unknown":
        return "UNASSIGNED"
    return f"{event.barrier}::{event.barrier_state}"


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main() -> int:
    settings = get_settings()
    ontology = get_ontology()
    pipeline = AnalysisPipeline(ontology, settings)

    eval_path = settings.eval_set_path
    if not eval_path.exists():
        print(f"eval set not found: {eval_path}")
        return 2
    doc = json.loads(eval_path.read_text(encoding="utf-8"))
    records = doc["records"]

    detail: list[dict] = []
    per_field_hits: Counter = Counter()
    per_field_total: Counter = Counter()
    cat_field_hits: dict[str, Counter] = defaultdict(Counter)
    cat_field_total: dict[str, Counter] = defaultdict(Counter)
    sif_correct = sif_total = 0
    lsr_correct = lsr_total = 0
    family_correct = family_total = 0
    schema_errors: list[str] = []

    critical = {
        "isolation_verified_vs_not": {"tp": 0, "n": 0},
        "hard_negative_no_false_negation": {"ok": 0, "n": 0},
        "same_family_grouping": {"ok": 0, "n": 0},
        "diff_activity_same_precursor": {"ok": 0, "n": 0},
        "verified_separation": {"ok": 0, "n": 0},
    }

    families_by_evall_id: dict[str, str] = {}

    for rec in records:
        rid = rec["report_id"]
        cat = rec["category"]
        narrative = rec["narrative"]
        gt = rec["ground_truth"]

        try:
            event = pipeline.analyze(rid, narrative, provider="rules").event
            schema_ok = True
        except Exception as exc:  # noqa: BLE001
            schema_errors.append(f"{rid}: {exc}")
            schema_ok = False
            event = None

        row = {
            "report_id": rid,
            "category": cat,
            "narrative": narrative,
            "provider": "rules",
            "schema_valid": schema_ok,
        }

        if event is None:
            detail.append(row)
            continue

        family_tag = predicted_family_tag(event)
        families_by_evall_id[rid] = family_tag

        for field in FIELDS:
            g = gt_field(rec, field)
            p = pred_field(event, field)
            hit = g == p
            if field == "location" and (not g or g == "unknown"):
                # Location is unconstrained in the ground truth.
                hit = True
                p = f"{p} (unconstrained)"
            per_field_hits[field] += hit
            per_field_total[field] += 1
            cat_field_hits[cat][field] += hit
            cat_field_total[cat][field] += 1
            row[field] = {"expected": g, "predicted": p, "match": hit}

        gt_sif = gt_field(rec, "sif_potential")
        pred_sif = _norm(event.sif.classification)
        sif_correct += gt_sif == pred_sif
        sif_total += 1
        row["sif"] = {"expected": gt_sif, "predicted": pred_sif,
                      "match": gt_sif == pred_sif}

        gt_lsr = {_norm(x) for x in gt.get("life_saving_rules", [])}
        pred_lsr = set(event.life_saving_rules or [])
        lsr_correct += gt_lsr == pred_lsr
        lsr_total += 1
        row["lsr"] = {"expected": sorted(gt_lsr), "predicted": sorted(pred_lsr),
                      "match": gt_lsr == pred_lsr}

        gt_fam = gt.get("family_tag", "UNASSIGNED")
        fam_match = family_tag == _norm(gt_fam)
        family_correct += fam_match
        family_total += 1
        row["family_tag"] = {"expected": gt_fam, "predicted": family_tag,
                             "match": fam_match}

        # Critical suite ---------------------------------------------------
        if cat == "negation":
            critical["isolation_verified_vs_not"]["n"] += 1
            g = gt.get("barrier_state")
            p = _norm(event.barrier_state)
            if p == g and g in ("verified", "not_verified"):
                critical["isolation_verified_vs_not"]["tp"] += 1
        if cat == "hard_negative":
            critical["hard_negative_no_false_negation"]["n"] += 1
            if gt.get("barrier_state") == "verified" and \
                    event.barrier_state == "verified":
                critical["hard_negative_no_false_negation"]["ok"] += 1
            # Verified records must never be grouped into failure families
            critical["verified_separation"]["n"] += 1
            if not family_tag.endswith("::not_verified") and not family_tag.endswith("::failed"):
                critical["verified_separation"]["ok"] += 1

        # Per-observation grouping evaluation: records with different wording
        # must group into the ground truth mechanism family tag
        if cat == "same_mechanism_diff_wording":
            critical["same_family_grouping"]["n"] += 1
            if family_tag == _norm(gt_fam):
                critical["same_family_grouping"]["ok"] += 1

        # Different activity same precursor: activity differences must not split mechanism
        if cat == "diff_activity_same_precursor":
            critical["diff_activity_same_precursor"]["n"] += 1
            if family_tag == _norm(gt_fam):
                critical["diff_activity_same_precursor"]["ok"] += 1

        detail.append(row)

    # ---- summary ----------------------------------------------------------
    schema_valid = (len(records) - len(schema_errors)) / len(records)
    field_acc = {f: (per_field_hits[f] / per_field_total[f])
                 if per_field_total[f] else 0.0 for f in FIELDS}
    sif_acc = sif_correct / sif_total if sif_total else 0.0
    lsr_acc = lsr_correct / lsr_total if lsr_total else 0.0
    family_acc = family_correct / family_total if family_total else 0.0
    neg_crit = critical["isolation_verified_vs_not"]
    hard_crit = critical["hard_negative_no_false_negation"]
    same_fam = critical["same_family_grouping"]

    # SIF macro-F1 (exact-match on the four classes)
    pred_by_id = {d["report_id"]: d["sif"]["predicted"] for d in detail}
    tp = {c: 0 for c in SIF_CLASSES}
    fp = {c: 0 for c in SIF_CLASSES}
    fn = {c: 0 for c in SIF_CLASSES}
    for rec in records:
        g = gt_field(rec, "sif_potential")
        p = pred_by_id.get(rec["report_id"], "unknown")
        if g in SIF_CLASSES and p in SIF_CLASSES:
            if g == p:
                tp[g] += 1
            else:
                fp[p] += 1
                fn[g] += 1
    prec = {c: (tp[c] / (tp[c] + fp[c])) if (tp[c] + fp[c]) else 0.0
            for c in SIF_CLASSES}
    rec_m = {c: (tp[c] / (tp[c] + fn[c])) if (tp[c] + fn[c]) else 0.0
             for c in SIF_CLASSES}
    f1 = {c: (2 * prec[c] * rec_m[c] / (prec[c] + rec_m[c]))
          if (prec[c] + rec_m[c]) else 0.0 for c in SIF_CLASSES}
    macro_f1 = sum(f1.values()) / len(SIF_CLASSES)

    summary = {
        "record_count": len(records),
        "schema_valid": round(schema_valid, 4),
        "field_accuracy": {k: round(v, 4) for k, v in field_acc.items()},
        "sif": {
            "exact_accuracy": round(sif_acc, 4),
            "macro_f1": round(macro_f1, 4),
            "per_class": {
                c: {"precision": round(prec[c], 4), "recall": round(rec_m[c], 4),
                    "f1": round(f1[c], 4)} for c in SIF_CLASSES
            },
        },
        "lsr": {"exact_set_accuracy": round(lsr_acc, 4)},
        "family": {"exact_tag_accuracy": round(family_acc, 4)},
        "critical_suite": {
            "isolation_verified_vs_not_verified": {
                "accuracy": round(neg_crit["tp"] / neg_crit["n"], 4) if neg_crit["n"] else None,
                "n": neg_crit["n"],
            },
            "hard_negative_no_false_negation": {
                "accuracy": round(hard_crit["ok"] / hard_crit["n"], 4) if hard_crit["n"] else None,
                "n": hard_crit["n"],
            },
            "same_family_grouping": {
                "accuracy": round(same_fam["ok"] / same_fam["n"], 4) if same_fam["n"] else None,
                "n": same_fam["n"],
            },
            "diff_activity_same_precursor": {
                "accuracy": round(critical["diff_activity_same_precursor"]["ok"] / critical["diff_activity_same_precursor"]["n"], 4) if critical["diff_activity_same_precursor"]["n"] else None,
                "n": critical["diff_activity_same_precursor"]["n"],
            },
            "verified_vs_failure_separation": {
                "accuracy": round(critical["verified_separation"]["ok"] / critical["verified_separation"]["n"], 4) if critical["verified_separation"]["n"] else None,
                "n": critical["verified_separation"]["n"],
            },
        },
        "category": {
            cat: {
                f: round(cat_field_hits[cat][f] / cat_field_total[cat][f], 4)
                if cat_field_total[cat][f] else None
                for f in FIELDS
            } | {
                "sif": round(
                    sum(1 for r in detail if r["category"] == cat
                        and r.get("sif", {}).get("match")) /
                    (len([r for r in detail if r["category"] == cat]) or 1),
                    4,
                )
            }
            for cat in cat_field_total
        },
        "schema_errors": schema_errors[:20],
    }

    out_dir = settings.eval_results_path
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(
        json.dumps({"summary": summary, "records": detail}, indent=2),
        encoding="utf-8",
    )

    # Persist a copy for /api/v1/evaluation/latest.
    try:
        from app.database import repos
        from datetime import datetime, timezone
        repos.save_evaluation(
            run_id=f"eval-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
            metrics={
                "record_count": len(records),
                "schema_valid": summary["schema_valid"],
                "field_accuracy": summary["field_accuracy"],
                "sif": summary["sif"],
                "lsr": summary["lsr"],
                "family": summary["family"],
                "critical_suite": summary["critical_suite"],
            },
            categories=summary["category"],
            counts={
                "records": len(records),
                "schema_errors": len(schema_errors),
                **{k: v["n"] for k, v in summary["critical_suite"].items()},
            },
        )
    except Exception as exc:  # noqa: BLE001  (persisting metrics must not fail the run)
        print(f"  (warning: could not persist evaluation row: {exc})")

    # ---- report ------------------------------------------------------------
    print(f"Evaluation: {len(records)} frozen records (provider=rules)")
    print(f"  schema_valid            {schema_valid:.3f}")
    for f in FIELDS:
        print(f"  {f:<22} {field_acc[f]:.3f}")
    print(f"  sif exact/tag           {sif_acc:.3f}  macro-F1 {macro_f1:.3f}")
    print(f"  lsr exact-set           {lsr_acc:.3f}")
    print(f"  family tag              {family_acc:.3f}")
    print("Critical suite:")
    for cname, v in summary["critical_suite"].items():
        print(f"  {cname:<40} {v['accuracy'] if v['accuracy'] is not None else 0:.3f}  "
              f"(n={v['n']})")
    print(f"  schema_errors           {len(schema_errors)}")
    if summary["category"]:
        worst = min(summary["category"],
                    key=lambda c: (summary["category"][c].get("barrier_state") or 1))
        print(f"  worst category by barrier_state: {worst} "
              f"({summary['category'][worst].get('barrier_state')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())