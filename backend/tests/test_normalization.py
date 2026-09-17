"""Normalization consistency invariants.

Safety-critical distinctions (barrier states, energy vs exposure) must survive
canonicalization. In particular ``verified`` and ``not_verified`` are distinct
canonical codes and are never cross-mapped, and multi-concept mentions must not
collapse a failure reading into a positive one.
"""

from __future__ import annotations

from app.services.normalization.canonical import (
    Canonicalizer,
    canonicalize_text,
    is_safety_critical_distinction_preserved,
)
from app.services.normalization.ontology import get_ontology

SIX_STATES = {"verified", "not_verified", "failed", "partially_effective",
              "absent", "unknown"}


def test_barrier_states_are_a_closed_distinct_set():
    onto = get_ontology()
    codes = {c.code for c in onto.concepts("barrier_state")}
    assert codes == SIX_STATES


def test_state_labels_round_trip_to_their_own_code():
    """Verified-like words must never map onto their negated counterpart."""
    onto = get_ontology()
    canon = Canonicalizer(onto)
    state = onto.concept("barrier_state", "verified")
    code, _ = canon.map(state.label, "barrier_state")
    assert code == "verified"
    state2 = onto.concept("barrier_state", "not_verified")
    code2, _ = canon.map(state2.label, "barrier_state")
    assert code2 == "not_verified"
    assert code != code2


def test_state_codes_never_cross_into_other_categories():
    onto = get_ontology()
    barrier_codes = {c.code for c in onto.concepts("barrier")}
    assert not (SIX_STATES & barrier_codes)
    energy_codes = {c.code for c in onto.concepts("energy")}
    assert not (SIX_STATES & energy_codes)


def test_canonicalization_preserves_distinct_codes():
    onto = get_ontology()
    canon = Canonicalizer(onto)
    code, _ = canon.map(onto.label("energy", "pressurized_gas"), "energy")
    assert code == "pressurized_gas"

    code2, _ = canon.map(onto.label("barrier", "energy_isolation"), "barrier")
    assert code2 == "energy_isolation"

    code3, _ = canon.map(onto.label("barrier", "hot_work_controls"), "barrier")
    assert code3 == "hot_work_controls"


def test_unknown_and_empty_are_normalized_to_unknown():
    onto = get_ontology()
    for term in ("", "unknown", "N/A", "-", None):
        assert canonicalize_text(term, "energy", onto)[0] == "unknown"


def test_multi_energy_primary_is_stable():
    """Same text, repeated calls -> identical canonical output (determinism)."""
    onto = get_ontology()
    canon = Canonicalizer(onto)
    multi = ("During welding inside the tank, both gas and stored energy "
             "were involved.")
    assert canon.map(multi, "activity") == canon.map(multi, "activity")
    assert canon.map(multi, "energy") == canon.map(multi, "energy")


def test_safety_critical_distinction_flag():
    assert is_safety_critical_distinction_preserved("barrier_state") is True