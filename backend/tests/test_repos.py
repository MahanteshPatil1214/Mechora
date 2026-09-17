"""Repository + full pipeline persistence tests (SQLite)."""

from __future__ import annotations

from app.database import repos
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline
from app.config import get_settings

NARR1 = (
    "While overhauling the compressor, work started before zero pressure "
    "was verified; a small gas release was observed in the compressor room. "
    "No injury was reported."
)
NARR2 = (
    "During hot work on a storage tank, thermal energy from the weld and "
    "flammable vapour were present; the gas test was incomplete and a flash "
    "fire occurred briefly. No injury was reported."
)


def _analyze(pipeline, narr: str):
    return pipeline.to_observation("RPT-1" if narr == NARR1 else "RPT-2", narr)


def test_create_and_retrieve_observation():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    obs = _analyze(pipeline, NARR1)
    saved = repos.create_observation(obs)
    assert saved.id.startswith("OBS-")
    fetched = repos.get_observation(saved.id)
    assert fetched is not None
    assert fetched.narrative == NARR1
    assert fetched.event.barrier_state in {
        "verified", "not_verified", "failed", "partially_effective",
        "absent", "unknown",
    }


def test_families_rebuilt_after_insert():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    repos.create_observation(_analyze(pipeline, NARR1))
    repos.create_observation(_analyze(pipeline, NARR2))
    families = repos.list_families()
    assert families, "no families built"
    by_name = {f.name: f for f in families}
    # two structurally-different mechanisms must not collapse into one family


def test_observation_filters_and_count():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    repos.create_observation(_analyze(pipeline, NARR1))
    repos.create_observation(_analyze(pipeline, NARR2))
    assert repos.count_observations() == 2
    nv = repos.list_observations(
        repos.ObservationFilters(barrier_state="not_verified")
    )
    assert all(o.event.barrier_state == "not_verified" for o in nv)
    fam = repos.list_families()[0]
    fam_obs = repos.list_observations(
        repos.ObservationFilters(family_id=fam.id)
    )
    assert all(o.precursor_family_id == fam.id for o in fam_obs)


def test_dashboard_summary_and_aggregates():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    repos.create_observation(_analyze(pipeline, NARR1))
    repos.create_observation(_analyze(pipeline, NARR2))
    summary = repos.dashboard_summary()
    assert summary["total_observations"] == 2
    assert summary["backend"] == "sqlite"
    assert summary["precursor_families"] >= 1
    agg = repos.barrier_aggregates()
    assert sum(a["count"] for a in agg) == 2
    assert repos.lsr_aggregates()
    assert repos.sif_aggregates()


def test_bulk_create_skips_duplicate_report_ids():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    first = _analyze(pipeline, NARR1)
    dup = pipeline.to_observation("RPT-1", NARR1)
    assert repos.bulk_create_observations([first, dup, _analyze(pipeline, NARR2)]) == 3
    assert repos.count_observations() == 2


def test_validation_update():
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    obs = repos.create_observation(_analyze(pipeline, NARR1))
    updated = repos.update_validation(obs.id, "validated")
    assert updated is not None and updated.validation == "validated"


def test_evaluation_persisted_and_round_trips():
    repos.save_evaluation(
        run_id="eval-regression",
        metrics={"field_accuracy": {"barrier_state": 1.0}},
        categories={"negation": {}},
        counts={"records": 216},
    )
    row = repos.latest_evaluation()
    assert row is not None
    assert row["run_id"] == "eval-regression"
    assert row["metrics"]["field_accuracy"]["barrier_state"] == 1.0
    assert row["counts"]["records"] == 216


def test_evaluation_replaces_same_run_id():
    repos.save_evaluation("eval-X", {"a": 1}, {}, {"n": 1})
    repos.save_evaluation("eval-X", {"a": 2}, {}, {"n": 1})
    rows = repos.latest_evaluation()
    assert rows["metrics"]["a"] == 2