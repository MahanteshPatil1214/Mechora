"""MECHORA dataset generator.

Generates the FROZEN labelled evaluation set (200+ narratives) and a larger
synthetic development set. The eval distribution follows PRD section 19/20:

  - 50+ same mechanism / different wording
  - 30+ negation (identical wording, opposite meaning)
  - 30+ different activity / same precursor
  - 30+ hard negatives (verified barriers, similar wording)
  - 20+ multi-hazard
  - 20+ ambiguous (may legitimately be unknown / needs_review)
  - verified-barrier no-precursor cases

Data is synthetic and representative; it is NOT OIL private data and no claim
is made that it represents OIL reporting language.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.models.safety_event import SafetyEvent  # noqa: E402
from app.services.normalization.ontology import get_ontology  # noqa: E402
from app.services.sif.sif import SIFAssessor  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


def _sif(energy: str, exposure: str, barrier: str, state: str,
         potential: str) -> str:
    """Ground-truth SIF using the same deterministic prototype rules."""
    event = SafetyEvent(
        report_id="GT",
        narrative="",
        activity="unknown",
        task_phase="unknown",
        energy=energy,
        exposure=exposure,
        barrier=barrier,
        barrier_state=state,
        potential_consequence=potential,
    )
    return SIFAssessor(get_ontology()).assess(event).classification


def _potential(energy: str, state: str) -> str:
    onto = get_ontology()
    if state in ("not_verified", "failed", "absent", "partially_effective"):
        if onto.energy_rank(energy) >= 4:
            return "serious_injury_or_fatality"
        return "injury"
    if energy != "unknown":
        if onto.energy_rank(energy) >= 4:
            return "serious_injury_or_fatality"
        return "injury"
    return "unknown"


# ----------------------------------------------------------------- activities
ACTIVITIES = {
    "pipeline_maintenance": [
        "During pipeline maintenance",
        "While repairing a pipeline flange",
        "During flange maintenance work",
    ],
    "compressor_maintenance": [
        "During compressor maintenance",
        "While overhauling the compressor",
        "During compressor servicing",
    ],
    "valve_replacement": [
        "During valve replacement",
        "While replacing a control valve",
        "During valve repair work",
    ],
    "pump_maintenance": [
        "During pump maintenance",
        "While servicing the transfer pump",
        "During pump overhaul work",
    ],
    "tank_maintenance": [
        "During tank maintenance",
        "While cleaning the storage tank",
        "During tank inspection work",
    ],
    "electrical_maintenance": [
        "During electrical maintenance",
        "While servicing the motor control panel",
        "During switchgear maintenance",
    ],
    "hot_work": ["During welding", "During hot work", "While gas cutting"],
    "confined_space_entry": [
        "During tank entry",
        "During confined space entry",
        "While entering the vessel",
    ],
    "working_at_height": [
        "During work at height",
        "While working on the elevated platform",
        "During scaffold work",
    ],
    "lifting_operations": [
        "During the crane lift",
        "During lifting operations",
        "While hoisting equipment",
    ],
}

LOCATION = {
    "pipeline_maintenance": "at the pipeline section",
    "compressor_maintenance": "in the compressor room",
    "valve_replacement": "at the process area",
    "pump_maintenance": "at the pump station",
    "tank_maintenance": "in the tank farm",
    "electrical_maintenance": "in the substation",
    "hot_work": "in the workshop",
    "confined_space_entry": "in the tank farm",
    "working_at_height": "in the process area",
    "lifting_operations": "in the storage yard",
}

# ----------------------------------------------- same-mechanism event clauses
NEG_EVENT_CLAUSES = [
    "work started before zero pressure was verified",
    "work proceeded without confirming that zero pressure was established",
    "work began before depressurization was confirmed",
    "isolation verification was skipped",
    "no one confirmed zero energy before the job began",
    "the job started while pressure had not yet been confirmed as zero",
    "the team commenced work having failed to confirm zero pressure",
    "zero pressure was never verified before work began",
    "the crew opened the system without verifying isolation",
    "work was carried out although zero-energy verification had not been done",
]

POS_EVENT_CLAUSES = [
    "work started only after zero pressure was verified",
    "zero pressure was confirmed before work began",
    "isolation was verified and locked out before work",
    "the line was depressurized and verified",
    "zero energy was confirmed by the crew before starting",
    "isolation verification was completed and signed off",
]

GAS_EXPOSURES = [
    ("uncontrolled_gas_release", "a small gas release was observed"),
    ("uncontrolled_gas_release", "gas was heard leaking from the flange"),
    ("uncontrolled_gas_release", "a hydrocarbon release occurred briefly"),
]

NO_INJURY = "No injury was reported."
MINOR = "A worker sustained a minor cut."

# Different wording of the same unresolved-isolation failure, used so that
# diff-activity records never share a full narrative with same-mechanism ones.
DIFF_CLAUSES = [
    "work started before zero energy was confirmed",
    "the crew opened the system without confirming pressure was absent",
    "work commenced before energy isolation verification was complete",
    "isolation of the line was not verified",
    "no isolation check was done before the job began",
    "the system was opened despite pressure not being confirmed as zero",
    "work began without a completed zero-energy check",
    "the flange was opened although depressurization was not verified",
    "isolation was not established before maintenance began",
    "work progressed before pressure verification was completed",
]

# ------------------------------------------------------------------ negation
NEGATION_PAIRS = [
    ("Isolation was verified before work commenced.",
     "Isolation was NOT verified before work commenced."),
    ("Zero pressure was confirmed.",
     "Zero pressure was not confirmed."),
    ("The line was proven depressurized.",
     "The line was not proven depressurized."),
    ("Lockout was checked by the supervisor.",
     "Lockout was not checked by the supervisor."),
    ("Energy isolation was verified before the job.",
     "Energy isolation was not verified before the job."),
    ("The permit was issued and valid.",
     "The permit was not issued."),
    ("Zero pressure had been confirmed.",
     "Zero pressure had not been confirmed."),
    ("Depressurization was verified.",
     "Depressurization was not verified."),
    ("The gas test was completed before entry.",
     "The gas test was NOT completed before entry."),
    ("Gas testing was carried out before work.",
     "Gas testing was not carried out before work."),
    ("The atmosphere was tested and found safe.",
     "The atmosphere was not tested."),
    ("The circuit was confirmed de-energized.",
     "The circuit was not confirmed de-energized."),
    ("Isolation checks were performed before work.",
     "Isolation checks were not performed before work."),
    ("Work permit verification was completed.",
     "Work permit verification was not completed."),
    ("The technician confirmed zero pressure before opening the flange.",
     "The technician did not confirm zero pressure before opening the flange."),
    ("Isolation of the system was verified.",
     "Isolation of the system was not verified."),
    ("The lockout was confirmed at the panel.",
     "The lockout was not confirmed at the panel."),
    ("Zero energy verification was carried out.",
     "Zero energy verification was not carried out."),
    ("The vent was opened and verified clear.",
     "The vent was not verified clear."),
    ("The crew checked that pressure was released.",
     "The crew did not check that pressure was released."),
]


def _gt_for_negation(sentence: str) -> dict:
    """Ground truth for a negation-pair sentence (mechanism-oriented)."""
    n = sentence.lower()
    neg = any(k in n for k in (" not ", " never ", "without", " no ", "did not"))
    barrier = "unknown"
    state = "verified" if not neg else "not_verified"
    energy = "unknown"
    exposure = "unknown"
    location = "unknown"
    if "zero pressure" in n or "depressur" in n or "line" in n:
        energy = "pressurized_gas"
        barrier = "energy_isolation"
    if "zero energy" in n:
        barrier = "energy_isolation"
    if "pressure" in n and energy == "unknown":
        energy = "pressurized_gas"
        barrier = "energy_isolation"
    if "vent" in n and barrier == "unknown":
        barrier = "energy_isolation"
    if "gas test" in n or "gas testing" in n:
        barrier = "hot_work_controls"
        energy = "flammable_atmosphere"
    if "atmosphere" in n:
        barrier = "confined_space_procedure"
    if "circuit" in n or "de-energ" in n:
        energy = "electrical_energy"
        barrier = "energy_isolation"
    if "permit" in n:
        barrier = "work_permit"
    if "lockout" in n:
        barrier = "energy_isolation"
        energy = "unknown"
    if "isolation" in n and barrier == "unknown":
        barrier = "energy_isolation"
    if "flange" in n:
        energy = "pressurized_gas"
        barrier = "energy_isolation"
    return {
        "activity": "unknown",
        "task_phase": "pre_job",
        "energy": energy,
        "barrier": barrier,
        "barrier_state": state,
        "exposure": exposure,
        "potential_consequence": _potential(energy, state),
        "sif_potential": _sif(energy, exposure, barrier, state,
                              _potential(energy, state)),
        "life_saving_rules": _lr(barrier, energy, exposure),
        "family_tag": _family_tag(barrier, state),
    }


# -------------------------------------------------------------------- helpers

def _lr(barrier: str, energy: str, exposure: str) -> list[str]:
    onto = get_ontology()
    table = onto.lsr_table()
    rules = list(table.get("barrier_to_rule", {}).get(barrier, []))
    if not rules:
        rules = list(table.get("energy_to_rule", {}).get(energy, []))
    if exposure in ("fire_or_explosion",) and "gas_testing" not in rules:
        rules.append("gas_testing")
    return rules


def _family_tag(barrier: str, state: str) -> str:
    if barrier == "unknown":
        return "UNASSIGNED"
    return f"{barrier}::{state}"


def _mk(rid: str, category: str, narrative: str, gt: dict) -> dict:
    return {
        "report_id": rid,
        "category": category,
        "narrative": narrative,
        "ground_truth": gt,
    }


# ------------------------------------------------------------------ builders

def build_same_mechanism(rng: random.Random) -> list[dict]:
    records: list[dict] = []
    rid = 0
    activities = ["pipeline_maintenance", "compressor_maintenance",
                  "valve_replacement", "pump_maintenance",
                  "tank_maintenance"]
    for act in activities:
        # different wording for the SAME mechanism
        clauses = NEG_EVENT_CLAUSES[:]
        rng.shuffle(clauses)
        for clause in clauses:
            dangerous = rng.random() < 0.85
            exposure, exp_phrase = rng.choice(GAS_EXPOSURES)
            consequence = MINOR if dangerous and rng.random() < 0.3 else NO_INJURY
            opener = rng.choice(ACTIVITIES[act])
            loc = LOCATION[act]
            narrative = (
                f"{opener}, {clause}; {exp_phrase} "
                f"{loc.lower()}. {consequence}"
            )
            rid += 1
            state = "not_verified"
            gt = {
                "activity": act,
                "task_phase": "maintenance",
                "energy": "pressurized_gas",
                "barrier": "energy_isolation",
                "barrier_state": state,
                "exposure": exposure,
                "potential_consequence": _potential("pressurized_gas", state),
                "sif_potential": _sif("pressurized_gas", exposure,
                                      "energy_isolation", state,
                                      _potential("pressurized_gas", state)),
                "life_saving_rules": _lr("energy_isolation", "pressurized_gas",
                                         exposure),
                "family_tag": _family_tag("energy_isolation", state),
            }
            records.append(_mk(f"EVAL-{rid:03d}",
                               "same_mechanism_diff_wording",
                               narrative, gt))
            if len(records) >= 200:
                break
        if len(records) >= 200:
            break
    return records


def build_negation() -> list[dict]:
    records: list[dict] = []
    rid = 0
    for pos, neg in NEGATION_PAIRS:
        for sentence, is_pos in ((neg, False), (pos, True)):
            gt = _gt_for_negation(sentence)
            rid += 1
            records.append(_mk(
                f"EVAL-{900 + rid:03d}", "negation", sentence, gt
            ))
    return records


def build_diff_activity(rng: random.Random) -> list[dict]:
    records: list[dict] = []
    clauses = DIFF_CLAUSES
    equipment_acts = ["pipeline_maintenance", "compressor_maintenance",
                      "valve_replacement", "pump_maintenance",
                      "tank_maintenance"]
    rid = 0
    for act in equipment_acts:
        for clause in clauses:
            exposure, exp_phrase = rng.choice(GAS_EXPOSURES)
            loc = LOCATION[act]
            narrative = (
                f"{rng.choice(ACTIVITIES[act])}, {clause}; "
                f"{exp_phrase} {loc.lower()}. {NO_INJURY}"
            )
            rid += 1
            state = "not_verified"
            gt = {
                "activity": act,
                "task_phase": "maintenance",
                "energy": "pressurized_gas",
                "barrier": "energy_isolation",
                "barrier_state": state,
                "exposure": exposure,
                "potential_consequence": _potential("pressurized_gas", state),
                "sif_potential": _sif("pressurized_gas", exposure,
                                      "energy_isolation", state,
                                      _potential("pressurized_gas", state)),
                "life_saving_rules": _lr("energy_isolation", "pressurized_gas",
                                         exposure),
                "family_tag": _family_tag("energy_isolation", state),
            }
            records.append(_mk(f"EVAL-{700 + rid:03d}",
                               "diff_activity_same_precursor", narrative, gt))
    return records


def build_hard_negatives(rng: random.Random) -> list[dict]:
    """Similar-failure-wording but the opposite safety meaning (verified)."""
    records: list[dict] = []
    roots = [
        ("isolation was verified before work", "energy_isolation", "unknown"),
        ("zero pressure was confirmed", "energy_isolation", "pressurized_gas"),
        ("depressurization was confirmed", "energy_isolation", "pressurized_gas"),
        ("energy isolation verification was completed", "energy_isolation", "unknown"),
        ("the permit was valid and in place", "work_permit", "unknown"),
        ("gas testing was completed and safe", "hot_work_controls",
         "flammable_atmosphere"),
        ("the atmosphere was tested and safe", "confined_space_procedure", "unknown"),
        ("the machine guard was present, fitted and checked before work",
         "machinery_guarding", "unknown"),
        ("fall protection was verified before work", "fall_protection", "unknown"),
        ("lockout was completed and checked", "energy_isolation", "unknown"),
    ]
    for i, (root, barrier, energy) in enumerate(roots):
        act = ["pipeline_maintenance", "compressor_maintenance",
               "valve_replacement", "pump_maintenance"]*5
        act = act[i % len(act)]
        narrative = f"During {rng.choice(ACTIVITIES[act])}, {root}. {NO_INJURY}"
        state = "verified"
        gt = {
            "activity": act,
            "task_phase": "maintenance",
            "energy": energy,
            "barrier": barrier,
            "barrier_state": state,
            "exposure": "unknown",
            "potential_consequence": _potential(energy, state),
            "sif_potential": _sif(energy, "unknown", barrier, state,
                                  _potential(energy, state)),
            "life_saving_rules": _lr(barrier, energy, "unknown"),
            "family_tag": _family_tag(barrier, state),
        }
        records.append(_mk(f"EVAL-{500 + i:03d}", "hard_negative",
                           narrative, gt))

    # same wording as failure case but flipped meaning (verified outcome)
    for i, (fail_phrase, ok_phrase) in enumerate([
        ("work started before zero pressure was verified",
         "work started after zero pressure was verified"),
        ("no one confirmed zero energy before the job",
         "zero energy was confirmed before the job"),
        ("isolation verification was skipped",
         "isolation verification was completed"),
        ("work began before depressurization was confirmed",
         "work began after depressurization was confirmed"),
        ("the crew proceeded without checking isolation",
         "the crew proceeded only after isolation checks were completed"),
        ("zero pressure was never verified",
         "zero pressure was fully verified"),
    ]):
        act = ["compressor_maintenance", "valve_replacement",
               "pump_maintenance", "pipeline_maintenance",
               "tank_maintenance", "compressor_maintenance"][i]
        narrative = (
            f"During {rng.choice(ACTIVITIES[act])}, {ok_phrase}; "
            f"the system remained closed during the work. {NO_INJURY}"
        )
        gt = {
            "activity": act,
            "task_phase": "maintenance",
            "energy": "pressurized_gas",
            "barrier": "energy_isolation",
            "barrier_state": "verified",
            "exposure": "unknown",
            "potential_consequence": _potential("pressurized_gas", "verified"),
            "sif_potential": _sif("pressurized_gas", "unknown",
                                  "energy_isolation", "verified",
                                  _potential("pressurized_gas", "verified")),
            "life_saving_rules": _lr("energy_isolation", "pressurized_gas",
                                     "unknown"),
            "family_tag": _family_tag("energy_isolation", "verified"),
        }
        records.append(_mk(f"EVAL-{600 + i:03d}", "hard_negative",
                           narrative, gt))

    # different mechanism with similar equipment vocabulary to failure cases
    diff_mech = [
        ("During pump maintenance the motor was found stopped; "
         "it had tripped on its overload relay and was reset after checking. "
         + NO_INJURY,
         "pump_maintenance", "moving_equipment", "machinery_guarding"),
        ("During electrical maintenance an earth leakage relay failed and "
         "tripped the circuit; an engineer reset it. " + NO_INJURY,
         "electrical_maintenance", "electrical_energy", "machinery_guarding"),
        ("During hot work a fire watch was present and a portable extinguisher "
         "was confirmed available. " + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls"),
        ("During confined space entry the vessel atmosphere was tested and "
         "ventilation was running. " + NO_INJURY,
         "confined_space_entry", "unknown", "confined_space_procedure"),
        ("During pipeline maintenance, the pressure was released and confirmed "
         "zero; the flange was opened and the line remained clear. "
         + NO_INJURY,
         "pipeline_maintenance", "pressurized_gas", "energy_isolation"),
        ("During pump maintenance, the pump was isolated and locked out "
         "before the casing was opened. " + NO_INJURY,
         "pump_maintenance", "unknown", "energy_isolation"),
        ("During valve replacement, the line was depressurized and vented "
         "before the valve was changed. " + NO_INJURY,
         "valve_replacement", "pressurized_gas", "energy_isolation"),
        ("During confined space entry, the vessel was purged and the "
         "atmosphere tested safe before entry. " + NO_INJURY,
         "confined_space_entry", "unknown", "confined_space_procedure"),
        ("During work at height, the platform had a guardrail and the harness "
         "was anchored and checked. " + NO_INJURY,
         "working_at_height", "gravity", "fall_protection"),
        ("During the crane lift, the lift plan was approved and the load path "
         "cleared before the lift. " + NO_INJURY,
         "lifting_operations", "unknown", "lifting_controls"),
        ("During electrical maintenance, the circuit was de-energized and "
         "proved dead before work began. " + NO_INJURY,
         "electrical_maintenance", "electrical_energy", "energy_isolation"),
        ("During hot work, the flammable gas test was completed and a fire "
         "watch was posted. " + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls"),
        ("During tank cleaning, the tank was ventilated and the atmosphere "
         "tested before entry. " + NO_INJURY,
         "tank_maintenance", "unknown", "confined_space_procedure"),
        ("During pipeline repair, the work permit was valid and signed by the "
         "supervisor. " + NO_INJURY,
         "pipeline_maintenance", "unknown", "work_permit"),
    ]
    for i, (narrative, act, energy, barrier) in enumerate(diff_mech):
        state = "verified"
        gt = {
            "activity": act,
            "task_phase": "maintenance",
            "energy": energy,
            "barrier": barrier,
            "barrier_state": state,
            "exposure": "unknown",
            "potential_consequence": _potential(energy, state),
            "sif_potential": _sif(energy, "unknown", barrier, state,
                                  _potential(energy, state)),
            "life_saving_rules": _lr(barrier, energy, "unknown"),
            "family_tag": _family_tag(barrier, state),
        }
        records.append(_mk(f"EVAL-{650 + i:03d}", "hard_negative",
                           narrative, gt))
    return records


def build_multi_hazard(rng: random.Random) -> list[dict]:
    records: list[dict] = []
    templates = [
        # hot work in tank with flammable + chemical residues; gas test skipped
        ("During hot work in a storage tank, flammable vapour was present and "
         "chemical residue remained, but gas testing was not completed before "
         "the job began; a flash fire flashed briefly. " + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls",
         "not_verified", "fire_or_explosion"),
        ("During confined space entry, an oxygen-deficient confined atmosphere "
         "was suspected and toxic fumes were reported, but ventilation checks "
         "were not verified before entry; the entrant felt dizzy. " + MINOR,
         "confined_space_entry", "chemical_exposure",
         "confined_space_procedure", "not_verified", "confined_space_atmosphere"),
        ("During pipeline maintenance, pressurized gas and flammable "
         "atmosphere were present; energy isolation was not verified and a "
         "gas release occurred. " + NO_INJURY,
         "pipeline_maintenance", "flammable_atmosphere", "energy_isolation",
         "not_verified", "uncontrolled_gas_release"),
        ("During electrical maintenance, an energized circuit and stored "
         "mechanical energy in a spring actuator were present; isolation was "
         "not confirmed before work and an arc flash was observed. " + NO_INJURY,
         "electrical_maintenance", "electrical_energy", "energy_isolation",
         "not_verified", "electrical_shock_risk"),
        ("During pump maintenance, rotating equipment and pressurized fluid "
         "were present; the machine guard was missing and a fluid release "
         "occurred. " + NO_INJURY,
         "pump_maintenance", "pressurized_gas", "machinery_guarding",
         "absent", "uncontrolled_gas_release"),
        ("During lifting operations, a suspended load was being moved over "
         "workers; the exclusion zone was not established. " + NO_INJURY,
         "lifting_operations", "gravity", "lifting_controls",
         "not_verified", "object_drop_struck_by"),
        ("During tank maintenance, chemical vapour and an oxygen-deficient "
         "atmosphere were present; forced ventilation failed during the job "
         "and vapour inhalation occurred. A worker reported a mild headache. "
         + NO_INJURY,
         "tank_maintenance", "chemical_exposure", "confined_space_procedure",
         "failed", "chemical_contact"),
        ("During hot work near a vent stack, flammable gas was present; the "
         "combustible gas test was partially effective and a small flash "
         "occurred. " + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls",
         "partially_effective", "fire_or_explosion"),
        ("During pump maintenance near a gas compressor, pressurized gas and "
         "rotating machinery were present; the pump guard was missing and a "
         "belt was caught briefly. " + NO_INJURY,
         "pump_maintenance", "pressurized_gas", "machinery_guarding",
         "absent", "caught_in_machinery"),
        ("During electrical maintenance in a gas facility, an energized panel "
         "and flammable vapour were present; the panel guard was removed and "
         "an arc flash occurred. " + NO_INJURY,
         "electrical_maintenance", "flammable_atmosphere",
         "machinery_guarding", "absent", "electrical_shock_risk"),
        ("During confined space entry, chemical vapour and an oxygen-deficient "
         "atmosphere were present; the forced-air ventilation was not running "
         "before entry. " + NO_INJURY,
         "confined_space_entry", "chemical_exposure",
         "confined_space_procedure", "not_verified", "confined_space_atmosphere"),
        ("During hot work on a storage tank, thermal energy from the weld and "
         "flammable vapour were present; the gas test was incomplete and a "
         "flash occurred. " + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls",
         "partially_effective", "fire_or_explosion"),
        ("During lifting near a process unit, a suspended load and pressurized "
         "gas lines were present; the lifting plan was skipped and the load "
         "swung close to the line. " + NO_INJURY,
         "lifting_operations", "pressurized_gas", "lifting_controls",
         "not_verified", "object_drop_struck_by"),
        ("During pipeline repair underground, pressurized gas was present; "
         "energy isolation was not verified and a gas release occurred during "
         "excavation. " + NO_INJURY,
         "pipeline_maintenance", "pressurized_gas", "energy_isolation",
         "not_verified", "uncontrolled_gas_release"),
        ("During confined space entry on a platform, flammable gas and moving "
         "equipment were present; the entry atmosphere checks were not done "
         "and gas was inhaled. " + NO_INJURY,
         "confined_space_entry", "flammable_atmosphere",
         "confined_space_procedure", "not_verified", "chemical_contact"),
        ("During compressor maintenance, pressurized gas and chemical hazards "
         "were present; isolation was partially effective and a hydrocarbon "
         "release occurred. " + NO_INJURY,
         "compressor_maintenance", "pressurized_gas", "energy_isolation",
         "partially_effective", "uncontrolled_gas_release"),
        ("During welding on a gas line, flammable gas was present; gas testing "
         "was not completed and a small flash occurred above the scaffold. "
         + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls",
         "not_verified", "fire_or_explosion"),
        ("During pump overhaul, stored mechanical energy in a spring and "
         "pressurized fluid were present; isolation lockout was not performed "
         "and a fluid release occurred. " + NO_INJURY,
         "pump_maintenance", "pressurized_gas", "energy_isolation",
         "not_verified", "uncontrolled_gas_release"),
        ("During electrical work on an offshore platform, live conductors and "
         "pressurized gas were present; isolation was not verified before the "
         "panel was opened and an arc flash occurred. " + NO_INJURY,
         "electrical_maintenance", "electrical_energy", "energy_isolation",
         "not_verified", "electrical_shock_risk"),
        ("During hot work in an enclosed area, flammable gas and toxic fumes "
         "were present; the fire watch was absent and a flash fire occurred. "
         + NO_INJURY,
         "hot_work", "flammable_atmosphere", "hot_work_controls",
         "absent", "fire_or_explosion"),
    ]
    for i, tpl in enumerate(templates):
        narrative, act, energy, barrier, state, exposure = tpl
        gt = {
            "activity": act,
            "task_phase": "maintenance",
            "energy": energy,
            "barrier": barrier,
            "barrier_state": state,
            "exposure": exposure,
            "potential_consequence": _potential(energy, state),
            "sif_potential": _sif(energy, exposure, barrier, state,
                                  _potential(energy, state)),
            "life_saving_rules": _lr(barrier, energy, exposure),
            "family_tag": _family_tag(barrier, state),
        }
        records.append(_mk(f"EVAL-{400 + i:03d}", "multi_hazard",
                           narrative, gt))
    return records


def build_ambiguous() -> list[dict]:
    records: list[dict] = []
    ambiguous = [
        ("During a routine team meeting a safety observation about the "
         "compressor area was noted for review.", "unknown", "unknown"),
        ("A worker was seen walking near the pump station.", "unknown",
         "pump_station"),
        ("The condition in the workshop requires further review.", "unknown",
         "workshop"),
        ("A report was submitted regarding the tank farm environment.",
         "unknown", "tank_farm"),
        ("The team discussed safety during the toolbox talk.", "unknown",
         "unknown"),
        ("An observation form was forwarded to the safety officer.", "unknown",
         "unknown"),
        ("The area appeared normal during the round.", "unknown", "unknown"),
        ("The contractor raised a concern about the process area.", "unknown",
         "process_area"),
        ("Details of the observation are incomplete and need clarification.",
         "unknown", "unknown"),
        ("A safety representative visited the substation and recorded a note.",
         "unknown", "substation"),
        ("The near-miss register entry for this facility is pending review.",
         "unknown", "unknown"),
        ("An unidentified issue was raised at the morning meeting.", "unknown",
         "unknown"),
        ("The worker mentioned something about conditions at height.",
         "gravity", "unknown"),
        ("A general observation about housekeeping was recorded.",
         "unknown", "unknown"),
        ("The shift handover noted an unresolved concern.", "unknown",
         "unknown"),
        ("The safety inspection checklist was partially filled for the yard.",
         "unknown", "unknown"),
        ("A comment regarding equipment was logged without further detail.",
         "unknown", "unknown"),
        ("The observer noted activity in the well site area.", "unknown",
         "well_site"),
        ("A suggestion was made to revisit the work procedure.", "unknown",
         "unknown"),
        ("The supervisor asked for a review of recent observations.",
         "unknown", "unknown"),
        ("An entry about the offshore platform was added to the log.",
         "unknown", "offshore_platform"),
        ("An observation about the yard area was logged for the shift.",
         "unknown", "unknown"),
        ("A worker reported a strange noise near the compressor.",
         "unknown", "unknown"),
        ("A handheld device alarmed during the walkthrough.",
         "unknown", "unknown"),
        ("An item was observed lying on the floor near the pump.",
         "unknown", "unknown"),
        ("Some equipment was returned to the store in good condition.",
         "unknown", "unknown"),
        ("The morning discussion covered several topics.",
         "unknown", "unknown"),
    ]
    for i, (narrative, energy, location) in enumerate(ambiguous[:26]):
        barrier = "housekeeping" if "housekeeping" in narrative else "unknown"
        if barrier == "unknown":
            state = "unknown"
        else:
            state = "unknown"
        gt = {
            "activity": "unknown",
            "task_phase": "unknown",
            "energy": energy,
            "barrier": barrier,
            "barrier_state": state,
            "exposure": "unknown",
            "potential_consequence": _potential(energy, state),
            "sif_potential": _sif(energy, "unknown", barrier, state,
                                  _potential(energy, state)),
            "life_saving_rules": _lr(barrier, energy, "unknown"),
            "family_tag": "UNASSIGNED",
        }
        if location != "unknown":
            gt["location"] = location
        records.append(_mk(f"EVAL-{300 + i:03d}", "ambiguous",
                           narrative, gt))
    return records


def write_dataset(path: Path, records: list[dict], kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "kind": kind,
        "version": "1.0",
        "note": ("Synthetic representative data for MECHORA prototype. "
                 "Not OIL private data; not trained on OIL data."),
        "record_count": len(records),
        "records": records,
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {kind}: {len(records)} records -> {path}")


def main() -> None:
    rng = random.Random(26165)
    records: list[dict] = []

    records += build_same_mechanism(rng)
    records += build_diff_activity(rng)
    records += build_negation()
    records += build_hard_negatives(rng)
    records += build_multi_hazard(rng)
    records += build_ambiguous()

    # dedupe by narrative
    seen: dict[str, dict] = {}
    for rec in records:
        seen.setdefault(rec["narrative"], rec)
    eval_records = list(seen.values())

    write_dataset(DATA / "evaluation" / "eval_set.json", eval_records, "evaluation")

    # ---- larger dev set from the same templating machinery ----
    dev: list[dict] = []
    for act in list(ACTIVITIES)[:9]:
        for clause in NEG_EVENT_CLAUSES:
            exposure, exp_phrase = rng.choice(GAS_EXPOSURES)
            dev.append(_mk(
                f"DEV-{len(dev) + 1:04d}",
                "synthetic_neg",
                f"{rng.choice(ACTIVITIES[act])}, {clause}; {exp_phrase} "
                f"{LOCATION[act]}. {NO_INJURY}",
                {
                    "activity": act, "task_phase": "maintenance",
                    "energy": "pressurized_gas",
                    "barrier": "energy_isolation",
                    "barrier_state": "not_verified",
                    "exposure": exposure,
                    "potential_consequence": _potential("pressurized_gas",
                                                        "not_verified"),
                    "sif_potential": _sif("pressurized_gas", exposure,
                                          "energy_isolation", "not_verified",
                                          _potential("pressurized_gas",
                                                     "not_verified")),
                    "life_saving_rules": _lr("energy_isolation",
                                             "pressurized_gas", exposure),
                    "family_tag": _family_tag("energy_isolation",
                                              "not_verified"),
                },
            ))
        for clause in POS_EVENT_CLAUSES:
            dev.append(_mk(
                f"DEV-{len(dev) + 1:04d}",
                "synthetic_pos",
                f"{rng.choice(ACTIVITIES[act])}, {clause}. {NO_INJURY}",
                {
                    "activity": act, "task_phase": "maintenance",
                    "energy": "pressurized_gas",
                    "barrier": "energy_isolation",
                    "barrier_state": "verified",
                    "exposure": "unknown",
                    "potential_consequence": _potential("pressurized_gas",
                                                        "verified"),
                    "sif_potential": _sif("pressurized_gas", "unknown",
                                          "energy_isolation", "verified",
                                          _potential("pressurized_gas",
                                                     "verified")),
                    "life_saving_rules": _lr("energy_isolation",
                                             "pressurized_gas", "unknown"),
                    "family_tag": _family_tag("energy_isolation", "verified"),
                },
            ))
    for i, state in enumerate(["failed", "absent", "partially_effective"]):
        state_phrases = {
            "failed": "the isolation valve failed during the operation",
            "absent": "no isolation was provided on the system",
            "partially_effective": "the isolation was only partially effective",
        }
        for act in list(ACTIVITIES)[:6]:
            dev.append(_mk(
                f"DEV-{len(dev) + 1:04d}",
                "synthetic_state",
                f"{rng.choice(ACTIVITIES[act])}, {state_phrases[state]}; "
                f"a small gas release occurred {LOCATION[act]}. {NO_INJURY}",
                {
                    "activity": act, "task_phase": "maintenance",
                    "energy": "pressurized_gas",
                    "barrier": "energy_isolation",
                    "barrier_state": state,
                    "exposure": "uncontrolled_gas_release",
                    "potential_consequence": _potential("pressurized_gas",
                                                        state),
                    "sif_potential": _sif("pressurized_gas",
                                          "uncontrolled_gas_release",
                                          "energy_isolation", state,
                                          _potential("pressurized_gas", state)),
                    "life_saving_rules": _lr("energy_isolation",
                                             "pressurized_gas",
                                             "uncontrolled_gas_release"),
                    "family_tag": _family_tag("energy_isolation", state),
                },
            ))
    write_dataset(DATA / "synthetic" / "dev_set.json", dev, "dev")


if __name__ == "__main__":
    main()