"""Negation-engine critical assertions (FR-04).

The engine is authoritative for barrier state. These tests protect the
core invariants: ``verified`` vs ``not_verified`` are never confused and
failures are never downgraded to ``verified``.
"""

from __future__ import annotations

from app.services.normalization.ontology import get_ontology
from app.services.negation.engine import NegationEngine

CASE_EQUIVALENTS = [
    ("energy_isolation", "The line was not proven depressurized.",
     "not_verified"),
    ("energy_isolation", "The line was proven depressurized.", "verified"),
    ("energy_isolation", "No one confirmed zero energy before the job began.",
     "not_verified"),
    ("energy_isolation", "Zero energy was confirmed before the job.", "verified"),
    ("energy_isolation", "The team commenced work having failed to confirm zero pressure.",
     "not_verified"),
    ("energy_isolation", "The crew opened the system without confirming pressure was absent.",
     "not_verified"),
    ("hot_work_controls", "The gas test was NOT completed before entry.", "not_verified"),
    ("hot_work_controls", "Gas testing was carried out before work.", "verified"),
    ("machinery_guarding", "The pump guard was missing.", "absent"),
    ("machinery_guarding", "The guard was present, fitted and checked.", "verified"),
    ("energy_isolation", "The isolator failed to hold.", "failed"),
    ("energy_isolation", "The isolation was partially effective; pressure crept back.",
     "partially_effective"),
    ("work_permit", "The permit was issued and valid.", "verified"),
    ("work_permit", "The permit was not issued.", "not_verified"),
    ("lifting_controls", "The exclusion zone was not established.", "not_verified"),
    ("fall_protection", "Fall protection was verified before work.", "verified"),
]


def _pair(a: str, b: str):
    eng = NegationEngine(get_ontology())
    sa = eng.classify_sentence(a).state
    sb = eng.classify_sentence(b).state
    return sa, sb


def test_verified_never_equals_not_verified():
    """FR-04 hard rule: the two states are separately reported."""
    eng = NegationEngine(get_ontology())
    verified_pairs = [
        ("The circuit was confirmed de-energized.", "verified"),
        ("Lockout was checked by the supervisor.", "verified"),
        ("Zero pressure had been confirmed.", "verified"),
        ("The atmosphere was tested and found safe.", "verified"),
        ("Depressurization was verified.", "verified"),
    ]
    for text, expected in verified_pairs:
        assert eng.classify_sentence(text).state == expected, text


def test_failure_signals_are_preserved():
    eng = NegationEngine(get_ontology())
    failures = [
        ("The guard failed and the shaft was exposed.", "failed"),
        ("The relief valve did not hold.", "failed"),
        ("There was no guard on the machine.", "absent"),
        ("The barrier was removed.", "absent"),
        ("The gas test was incomplete.", "partially_effective"),
    ]
    for text, expected in failures:
        assert eng.classify_sentence(text).state == expected, text


def test_equivalent_negation_pairs_are_opposite():
    """The two listed outcomes of the same sentence must be opposites."""
    pairs = [
        ("The line was not proven depressurized.",
         "The line was proven depressurized."),
        ("No one confirmed zero energy.",
         "Zero energy was confirmed."),
        ("The permit was not issued.", "The permit was issued and valid."),
        ("The atmosphere was not tested.",
         "The atmosphere was tested and found safe."),
        ("Lockout was not checked by the supervisor.",
         "Lockout was checked by the supervisor."),
        ("The gas test was not completed.",
         "The gas test was completed."),
    ]
    eng = NegationEngine(get_ontology())
    for neg, pos in pairs:
        sne = eng.classify_sentence(neg).state
        spo = eng.classify_sentence(pos).state
        assert sne == "not_verified", (neg, sne)
        assert spo == "verified", (pos, spo)


def test_protective_device_trip_is_verified_not_failed():
    eng = NegationEngine(get_ontology())
    s = eng.classify_barrier(
        "machinery_guarding",
        "The motor was found stopped; it had tripped on its overload relay "
        "and was reset after checking.",
    ).state
    assert s == "verified"


def test_unknown_when_no_evidence():
    eng = NegationEngine(get_ontology())
    assert eng.classify_sentence(
        "A general observation was recorded."
    ).state == "unknown"
    assert eng.classify_barrier(
        "lifting_controls", "A general observation was recorded."
    ).state == "unknown"


def test_closed_state_set():
    eng = NegationEngine(get_ontology())
    valid = {"verified", "not_verified", "failed", "partially_effective",
             "absent", "unknown"}
    for _barrier, text, _expected in CASE_EQUIVALENTS:
        state = eng.classify_sentence(text).state
        assert state in valid