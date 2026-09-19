"""Document segmentation layer tests.

Covers:
    1. ReportSegmenter structural rules (unit level)
    2. Bug 3 regression: barrier evidence vs barrier-STATE evidence
    3. Bug 2 regression: negated consequence -> none_identified
    4. End-to-end: multi-observation documents analyzed independently; the
       "Expected Test Signals" instructional block never contaminates ANY
       report's narrative, evidence or traceability
"""

from __future__ import annotations

import io

from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.api.routes import documents
from app.config import get_settings
from app.services.document_segmentation.segmenter import ReportSegmenter
from app.services.normalization.ontology import get_ontology
from app.services.pipeline import AnalysisPipeline

REPORT1 = (
    "The mechanical technician loosened the bonnet studs on the crude pump "
    "suction strainer at the pump station before cracking the bleeder needle "
    "valve to confirm depressurization. The strainer contained pressurized "
    "liquid but isolation was not verified. A hazardous liquid release was "
    "uncontrolled. No injury occurred and no medical treatment was required."
)
REPORT2 = (
    "At the gas compressor skid the operator attempted a valve purge while the "
    "vessel remained under pressure. Zero-energy was never confirmed before "
    "work began, and gas was released during the attempt."
)
EXPECTED_SIGNALS = (
    "Expected Test Signals\n"
    "bubbling\n"
    "hisssing\n"
    "whistling\n"
    "These signals indicate a leak and are only for validation."
)


MULTI_DOC = (
    f"Report 1\n"
    f"Plant: Refinery X\n"
    f"Date: 2026-09-19\n"
    f"{REPORT1}\n"
    f"\n"
    f"Report 2 - Gas Compressor Narrative\n"
    f"{REPORT2}\n"
    f"\n"
    f"{EXPECTED_SIGNALS}\n"
)


# ------------------------------------------------------------- segmentation


def test_splits_multi_observation_document_into_independent_reports():
    segments = ReportSegmenter().reports(MULTI_DOC)
    assert len(segments) == 2
    assert segments[0].heading == "Report 1"
    assert REPORT1 in segments[0].text
    assert segments[1].heading == "Report 2 - Gas Compressor Narrative"
    assert REPORT2 in segments[1].text


def test_metadata_and_expected_signals_excluded_from_reports():
    segments = ReportSegmenter().reports(MULTI_DOC)
    for seg in segments:
        assert "Plant:" not in seg.text
        assert "Refinery X" not in seg.text
        assert "Date:" not in seg.text
        assert "Expected Test Signals" not in seg.text
        assert "bubbling" not in seg.text
        assert "hisssing" not in seg.text
        assert "these signals indicate" not in seg.text.lower()


NON_REPORT_TOKENS = (
    "Expected Test Signals",
    "Expected Signals",
    "instructions",
    "bubbling",
    "hisssing",
    "whistling",
    "only for validation",
    "NON-REPORT",
)


def _assert_zero_non_report_tokens(text: str) -> None:
    low = text.lower()
    for token in NON_REPORT_TOKENS:
        assert token.lower() not in low, f"non-report token leaked: {token!r}"


def test_report2_contains_zero_expected_signals_tokens():
    segments = ReportSegmenter().reports(MULTI_DOC)
    assert len(segments) == 2
    _assert_zero_non_report_tokens(segments[1].text)


def test_nonreport_marker_heading_terminates_report_segment():
    # The uploaded demo document: REPORT 1 / REPORT 2 / NON-REPORT block.
    doc = (
        "REPORT 1\n"
        "Pump maintenance \u2192 pressurized liquid \u2192 isolation NOT VERIFIED\n"
        "\n"
        "REPORT 2\n"
        "Compressor maintenance \u2192 pressurized gas \u2192 isolation "
        "NOT VERIFIED\n"
        "\n"
        "NON-REPORT\n"
        "Expected Test Signals / instructions\n"
    )
    segments = ReportSegmenter().segment(doc)
    assert [s.kind for s in segments] == ["report", "report", "non_report"]
    assert [s.heading for s in segments] == [
        "REPORT 1", "REPORT 2", "NON-REPORT"]
    # Report 2 carries zero characters from the non-report block.
    _assert_zero_non_report_tokens(segments[1].text)
    assert segments[1].character_count == len(segments[1].text)
    # The NON-REPORT block is one segment holding the marker + instructions.
    assert "Expected Test Signals / instructions" in segments[2].text
    # Character totals must not include the NON-REPORT block.
    report_chars = sum(s.character_count for s in segments if s.kind == "report")
    assert report_chars < len(doc)


def test_instructional_heading_glued_to_report2_body_terminates_segment():
    # No blank line between REPORT 2's body and the instructional block: the
    # boundary heading must still terminate the report segment.
    doc = (
        "Report 2 - Gas Compressor Narrative\n"
        f"{REPORT2}\n"
        f"{EXPECTED_SIGNALS}\n"
    )
    segments = ReportSegmenter().segment(doc)
    assert [s.kind for s in segments] == ["report", "non_report"]
    # REPORT 2 is clean: zero tokens from the instructional block.
    _assert_zero_non_report_tokens(segments[0].text)
    assert "Expected Test Signals" in segments[1].text
    assert segments[1].kind == "non_report"


def test_nonreport_content_never_appears_in_evidence():
    # Full pipeline (rules path) over a segmented document: non-report tokens
    # must never surface in narrative or any field_evidence value.
    doc = (
        "Report 1\n"
        f"{REPORT1}\n"
        "\n"
        "Report 2\n"
        f"{REPORT2}\n"
        f"{EXPECTED_SIGNALS}\n"
    )
    segments = ReportSegmenter().reports(doc)
    assert len(segments) == 2
    for seg in segments:
        event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
            "R2", seg.text, provider="rules"
        ).event
        _assert_zero_non_report_tokens(seg.text)
        assert "NON-REPORT" not in event.narrative
        for evidence in event.field_evidence.values():
            if evidence:
                _assert_zero_non_report_tokens(evidence)


def test_heading_not_included_in_report_narrative():
    segments = ReportSegmenter().reports(MULTI_DOC)
    assert not segments[0].text.startswith("Report 1")
    assert REPORT1 in segments[0].text


def test_page_footers_and_bare_digits_filtered():
    text = (
        f"Report 1\nPage 1 of 3\n{REPORT1}\n\n"
        f"Report 2\n3\n{REPORT2}\n"
    )
    segments = ReportSegmenter().reports(text)
    assert len(segments) == 2
    for seg in segments:
        assert "Page 1 of 3" not in seg.text
        assert seg.text.strip() != "3"
    assert segments[0].text == REPORT1
    assert segments[1].text == REPORT2


def test_blank_line_boundary_joins_consecutive_report_paragraphs():
    text = "Report 7\n\nFirst paragraph only.\n\nSecond paragraph here.\n"
    segments = ReportSegmenter().reports(text)
    assert len(segments) == 1
    assert "First paragraph only." in segments[0].text
    assert "Second paragraph here." in segments[0].text


def test_txt_with_plain_body_is_single_report_segment():
    segments = ReportSegmenter().reports(REPORT1)
    assert len(segments) == 1
    assert segments[0].text == REPORT1


def test_utf8_bom_does_not_break_first_heading():
    segments = ReportSegmenter().reports(f"\ufeff{MULTI_DOC}")
    assert len(segments) == 2
    assert segments[0].heading == "Report 1"
    assert segments[0].text.startswith("The mechanical technician")


# ------------------------------------------------------- Bug 3 regression


def test_bug3_barrier_evidence_vs_barrier_state_evidence():
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "R1", REPORT1, provider="rules"
    ).event
    # Barrier VALUE = energy_isolation; barrier evidence = verification phrase.
    assert event.barrier == "energy_isolation"
    assert event.field_evidence["barrier"] == (
        "before cracking the bleeder needle valve to confirm depressurization"
    )
    # Barrier STATE = not_verified; state evidence = full causal sentence.
    assert event.barrier_state == "not_verified"
    assert event.field_evidence["barrier_state"] == (
        "The mechanical technician loosened the bonnet studs on the crude pump "
        "suction strainer at the pump station before cracking the bleeder needle "
        "valve to confirm depressurization."
    )
    # The state evidence contains the barrier evidence (sentence ⊃ phrase).
    assert event.field_evidence["barrier"] in event.field_evidence["barrier_state"]


# ------------------------------------------------------- Bug 2 regression


def test_bug2_negated_consequence_is_none_identified_with_full_sentence_evidence():
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "R1", REPORT1, provider="rules"
    ).event
    assert event.actual_consequence == "none_identified"
    assert event.field_basis["actual_consequence"] == "explicit"
    assert event.field_evidence["actual_consequence"] == (
        "No injury occurred and no medical treatment was required."
    )


def test_negated_consequence_never_read_back_as_positive():
    narrative = (
        "During flange maintenance, isolation was not verified and gas was "
        "released. No medical treatment was required and no injury occurred."
    )
    event = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "FLG", narrative, provider="rules"
    ).event
    assert event.actual_consequence == "none_identified"
    assert "medical treatment" in event.field_evidence.get("actual_consequence", "")


def test_llm_path_negated_consequence_matches_rules_path():
    """Provider-independence for Bug 2: when an LLM proposes none_identified
    for a negated-consequence narrative, the deterministic layer grounds it the
    same way as the rules path — full-sentence evidence, NEVER read back as a
    positive consequence."""
    narrative = (
        "During maintenance, the technician loosened a bonnet stud before the "
        "pressure was confirmed safe, and liquid sprayed out. No injury occurred "
        "and no medical treatment was required."
    )
    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    out = pipeline.rule_extractor.extract("LNEG-1", narrative)
    pipeline.llm_extractor.extract = (
        lambda _rid, _narr: (out.extraction, {"provider": "llm"})
    )
    ev_llm = pipeline.analyze("LNEG-2", narrative, provider="llm").event
    ev_rules = AnalysisPipeline(get_ontology(), get_settings()).analyze(
        "LNEG-3", narrative, provider="rules"
    ).event
    assert ev_llm.actual_consequence == "none_identified"
    assert ev_llm.actual_consequence == ev_rules.actual_consequence
    assert ev_llm.field_evidence.get("actual_consequence") == \
        ev_rules.field_evidence.get("actual_consequence")
    assert ev_llm.field_basis["actual_consequence"] == \
        ev_rules.field_basis["actual_consequence"]


# ------------------------------------------------------------------- API


def _upload(filename: str, data: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_analyze_segments_report_1_semantics():
    res = documents.analyze_document(
        _upload("demo.txt", MULTI_DOC.encode("utf-8"), "text/plain")
    )
    assert res.report_count == 2
    assert res.observations_created == 2

    seg1 = res.analyses[0]
    ev1 = seg1.analysis.event
    assert seg1.analysis.report_segment_id == seg1.analysis.report_id
    assert ev1["activity"] == "pump_maintenance"
    assert ev1["energy"] == "pressurized_liquid"
    assert ev1["barrier"] == "energy_isolation"
    assert ev1["barrier_state"] == "not_verified"
    assert ev1["location"] == "pump_station"
    assert ev1["actual_consequence"] == "none_identified"
    assert ev1["exposure"] == "uncontrolled_liquid_release"


def test_analyze_expected_signals_never_contaminate_any_report():
    res = documents.analyze_document(
        _upload("demo.txt", MULTI_DOC.encode("utf-8"), "text/plain")
    )
    assert res.report_count == 2
    for seg in res.analyses:
        assert seg.analysis is not None
        narrative = seg.analysis.event["narrative"]
        evidence = seg.analysis.event.get("field_evidence", {})
        assert "Expected Test Signals" not in narrative
        assert "bubbling" not in narrative
        assert "hisssing" not in narrative.lower()
        assert "Expected Test Signals" not in " ".join(evidence.values())
        assert "bubbling" not in " ".join(evidence.values())


def test_report_2_analyzed_independently():
    res = documents.analyze_document(
        _upload("demo.txt", MULTI_DOC.encode("utf-8"), "text/plain")
    )
    seg2 = res.analyses[1]
    ev2 = seg2.analysis.event
    # Report 2's own evidence base: gas compressor narrative only.
    assert "pump station" not in ev2["narrative"]
    assert ev2["energy"] == "pressurized_gas"


def test_extract_returns_segments_and_report_count():
    body = documents.extract_document(
        _upload("demo.txt", MULTI_DOC.encode("utf-8"), "text/plain")
    )
    assert body.report_count == 2
    kinds = [s.kind for s in body.segments]
    assert kinds.count("report") == 2
    assert any(s.kind == "non_report" for s in body.segments)
    heading = [s for s in body.segments if s.heading == "Expected Test Signals"]
    assert heading and heading[0].kind == "non_report"


def test_non_report_only_document_warns_and_analyzes_zero():
    only_metadata = "Plant: Refinery X\nDate: 2026-09-19\nExpected Test Signals\nbubbling\n"
    res = documents.analyze_document(
        _upload("notes.txt", only_metadata.encode("utf-8"), "text/plain")
    )
    assert res.report_count == 0
    assert res.observations_created == 0
    assert res.analyses == []
    assert any("no report segments" in w for w in res.warnings)


def test_metadata_location_not_used_as_evidence():
    res = documents.analyze_document(
        _upload("demo.txt", MULTI_DOC.encode("utf-8"), "text/plain")
    )
    # Location metadata is dropped (non-report), but the narrative itself names
    # the pump station, so Report 1 still locates correctly.
    seg1 = res.analyses[0]
    assert seg1.analysis.event["location"] == "pump_station"
    assert "Location:" not in seg1.analysis.event["narrative"]