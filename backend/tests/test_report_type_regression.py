"""Report type persistence regression tests.

Reporter-selected classification (``ua_uc`` | ``near_miss`` | ``incident``)
must SURVIVE the full chain — the selected value is saved with the observation
and read back identically through the persistence layer, for BOTH intake paths:

    * manual single-observation analyze (JSON)
    * document upload (multipart) — one type per document, applied to every
      report segment

This guards a past regression where the selected type was dropped on write and
every observation silently persisted as ``ua_uc`` regardless of reporter input.
It also pins the intent: ``report_type`` is REPORTER metadata, never an analysis
input — it must never alter event extraction or precursor-family clustering.
"""

from __future__ import annotations

import io

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.api.routes import analyze as analyze_route
from app.api.routes import documents as documents_route
from app.database import repos

TYPES = ("ua_uc", "near_miss", "incident")

NARRATIVE = (
    "During routine flange maintenance on the gas line, the fitter opened "
    "the flange before confirming zero energy, releasing a small volume of "
    "gas to atmosphere. The fitter was not injured."
)

MULTI_REPORTS = (
    "HSE Safety Observation Report\n"
    "Plant: Refinery X\n"
    "Date: 2026-09-19\n"
    "Report 1\n"
    "The mechanical technician loosened the bonnet studs on the crude pump "
    "suction strainer at the pump station before cracking the bleeder needle "
    "valve to confirm depressurization. The strainer contained pressurized "
    "liquid but isolation was not verified. A hazardous liquid release was "
    "uncontrolled. No injury occurred and no medical treatment was required.\n"
    "Report 2 - Gas Compressor Narrative\n"
    "At the gas compressor skid the operator attempted a valve purge while the "
    "vessel remained under pressure. Zero-energy was never confirmed before "
    "work began, and gas was released during the attempt. Nobody was hurt.\n"
    "Expected Test Signals\n"
    "This instructional block must never become a report segment: it is "
    "metadata for validation only.\n"
)


def _upload(filename: str, data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _manual(report_id: str, report_type: str, narrative: str = NARRATIVE) -> str:
    """Drive the manual JSON analyze route; return the persisted obs id."""
    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id=report_id,
            narrative=narrative,
            provider="rules",
            report_type=report_type,
        )
    )
    saved = repos.get_observation(res.id)
    return saved.id


# ------------------------------------------------------------------- JSON path


def test_all_three_report_types_are_saved():
    for report_type in TYPES:
        obs_id = _manual(f"RTP-{report_type}-1", report_type)
        saved = repos.get_observation(obs_id)
        assert saved.report_type == report_type
        assert saved.report_id == f"RTP-{report_type}-1"


def test_default_report_type_is_saved_as_unknown():
    # Reporter did not pick a type -> persisted as ``unknown``, never silently
    # fabricated as ua_uc. The pipeline must not raise on the honest default.
    res = analyze_route.analyze(
        analyze_route.AnalyzeRequest(
            report_id="RTP-DEF-1", narrative=NARRATIVE, provider="rules"
        )
    )
    saved = repos.get_observation(res.id)
    assert saved.report_type == "unknown"


def test_report_type_is_reporter_metadata_not_analysis_input():
    """Same narrative, all three types: identical extracted event + precursor
    family. report_type is METADATA only — it must not reshuffle clustering."""
    narrative = (
        "During hydraulic pump alignment checks the fitter reached around the "
        "unrestrained guard towards the moving coupling while the pump was "
        "running. No contact occurred and nobody was injured."
    )
    events: dict[str, tuple] = {}
    family_ids: set[str] = set()
    for report_type in TYPES:
        obs_id = _manual(f"RTP-META-{report_type}", report_type, narrative)
        saved = repos.get_observation(obs_id)
        ev = saved.event
        events[report_type] = (
            ev.barrier, ev.energy, ev.barrier_state,
            ev.activity, ev.exposure,
        )
        family_ids.add(saved.precursor_family_id)
    base = events["ua_uc"]
    for report_type in ("near_miss", "incident"):
        assert events[report_type] == base, report_type
    assert len(family_ids) == 1


# ---------------------------------------------------------------- upload path


USER_NARRATIVE = (
    "During routine maintenance on the gas lift manifold located on the "
    "South Production Module (Deck Level +24m), the fitter proceeded to "
    "loosen a joint on line GL-08 without prior zero-energy verification. "
    "Residual pressure breached the gasket seal, resulting in a short-"
    "duration gas release."
)


def test_activity_and_location_extract_from_user_narrative_not_unknown():
    """THE regression the reporter filed: for THEIR vocabulary the engine
    persisted activity/location as UNKNOWN. With the ontology synonyms now
    covering these terms, the saved event must carry the codes — never
    silently dropping to the unknown fallback for every type."""
    for report_type in TYPES:
        obs_id = _manual(f"RTP-USER-{report_type}", report_type, USER_NARRATIVE)
        saved = repos.get_observation(obs_id)
        assert saved.event.activity != "unknown", report_type
        assert saved.event.location != "unknown", report_type
        assert saved.report_type == report_type, report_type


def test_document_upload_applies_report_type_to_every_segment():
    res = documents_route.analyze_document(
        _upload("multi.txt", MULTI_REPORTS.encode("utf-8"), "text/plain"),
        report_type="incident",
    )
    assert res.report_count == 2
    for seg in res.analyses:
        saved = repos.get_observation(seg.analysis.id)
        assert saved.report_type == "incident", seg.report_segment_id


def test_document_upload_persists_each_of_the_three_types():
    for report_type in TYPES:
        res = documents_route.analyze_document(
            _upload(
                f"multi-{report_type}.txt",
                MULTI_REPORTS.encode("utf-8"),
                "text/plain",
            ),
            report_type=report_type,
        )
        for seg in res.analyses:
            saved = repos.get_observation(seg.analysis.id)
            assert saved.report_type == report_type, seg.report_segment_id


# ------------------------------------------------------ API read-back path


def test_observation_list_api_reads_back_stored_report_type():
    """The GET /observations serializer must surface the PERSISTED report
    type, never a schema-default fabrication. Regression: the route previously
    dropped report_type/document_id/report_segment_id/segment_index, so every
    row serialized as 'ua_uc' regardless of the stored value."""
    from app.api.routes import observations as observations_route
    from app.schemas.api import ObservationOut

    for rt, rid in (("near_miss", "RTP-LIST-1"), ("incident", "RTP-LIST-2"),
                    ("unknown", "RTP-LIST-3")):
        _manual(rid, rt)

    rows = repos.list_observations(
        repos.ObservationFilters(q="RTP-LIST", limit=50)
    )
    by_id = {o.report_id: o for o in rows if "RTP-LIST" in o.report_id}
    assert len(by_id) == 3
    for report_id, expected in {
        "RTP-LIST-1": "near_miss",
        "RTP-LIST-2": "incident",
        "RTP-LIST-3": "unknown",
    }.items():
        out = ObservationOut.model_validate(
            observations_route._to_out(by_id[report_id])
        )
        assert out.report_type == expected, report_id
        assert out.document_id == ""
        assert out.report_segment_id == ""


def test_observation_detail_api_reads_back_stored_report_type():
    from app.api.routes import observations as observations_route
    from app.schemas.api import ObservationOut

    obs_id = _manual("RTP-DET-1", "ua_uc")
    saved = repos.get_observation(obs_id)
    out = ObservationOut.model_validate(observations_route._to_out(saved))
    assert out.id == obs_id
    assert out.report_type == "ua_uc"
