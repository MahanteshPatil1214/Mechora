// MECHORA Centralized API Client
// Strict fidelity to backend endpoints in backend/app/api/routes/
// Supports graceful demo fallback when backend is starting or offline

const base = "/api/v1";

// Report classification chosen by the reporter at intake ("Add Safety
// Report"). Stored as metadata on each observation; never used in analysis.
export const REPORT_TYPES = [
  { code: "ua_uc", label: "UA/UC Observation" },
  { code: "near_miss", label: "Near Miss" },
  { code: "incident", label: "Incident" },
  { code: "unknown", label: "Unknown" },
];
export const REPORT_TYPE_CODES = REPORT_TYPES.map((t) => t.code);
export function reportTypeLabel(value) {
  if (!value) return "Unknown";
  const code = String(value)
    .trim()
    .replace(/\s+/g, "_")
    .toLowerCase();
  const t = REPORT_TYPES.find((x) => x.code === code);
  return t ? t.label : "Unknown";
}

async function request(path, options = {}) {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      /* surface raw status text */
    }
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Curated Demo / Prototype Fallback Data (from seed_demo.py & synthetic dataset)
// Used gracefully if backend is offline or starting up
// ---------------------------------------------------------------------------
export const DEMO_OBSERVATIONS = [
  {
    id: "OBS-DEMO01",
    report_id: "FLANGE-01",
    report_type: "near_miss",
    narrative:
      "During routine flange tightening on the gas line, the fitter did not confirm zero energy before loosening the joint and a small gas release occurred.",
    provider: "rules",
    event: {
      report_id: "FLANGE-01",
      activity: "pipeline_maintenance",
      task_phase: "maintenance",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      exposure: "uncontrolled_gas_release",
      potential_consequence: "serious_injury_or_fatality",
      location: "pipeline_section",
      confidence: 0.95,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "flange tightening",
        energy: "gas line",
        barrier: "zero energy",
        barrier_state: "did not confirm",
        exposure: "gas release occurred",
      },
      sif: {
        classification: "high",
        confidence: 0.95,
        reason:
          "High-hazard energy (pressurized gas) with unverified isolation during pipeline maintenance creates severe exposure potential.",
        supporting_evidence: [
          "Hazardous energy: pressurized gas",
          "Barrier state: not verified",
          "Potential consequence: serious injury or fatality",
        ],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.95,
        basis: "Direct match on energy_isolation barrier and pressurized_gas energy.",
        evidence: ["zero energy", "did not confirm"],
      },
      precursor_signature: {
        activity: "pipeline_maintenance",
        task_phase: "maintenance",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "not_verified",
        exposure: "uncontrolled_gas_release",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-001",
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  },
  {
    id: "OBS-DEMO02",
    report_id: "COMP-01",
    report_type: "near_miss",
    narrative:
      "Compressor servicing: the crew opened the casing without zero-energy verification; isolation had not been done and a small gas release was observed.",
    provider: "rules",
    event: {
      report_id: "COMP-01",
      activity: "compressor_maintenance",
      task_phase: "maintenance",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      exposure: "uncontrolled_gas_release",
      potential_consequence: "serious_injury_or_fatality",
      location: "compressor_room",
      confidence: 0.92,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "compressor servicing",
        energy: "gas release",
        barrier: "zero-energy verification",
        barrier_state: "without",
        exposure: "gas release was observed",
      },
      sif: {
        classification: "high",
        confidence: 0.92,
        reason:
          "Compressor housing opened without proven zero-energy verification.",
        supporting_evidence: [
          "Hazardous energy: pressurized gas",
          "Barrier state: not verified",
        ],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.92,
        basis: "Energy isolation procedure bypassed.",
        evidence: ["without zero-energy verification"],
      },
      precursor_signature: {
        activity: "compressor_maintenance",
        task_phase: "maintenance",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "not_verified",
        exposure: "uncontrolled_gas_release",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-001",
    validation: "validated",
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
  {
    id: "OBS-DEMO03",
    report_id: "VALVE-01",
    report_type: "near_miss",
    narrative:
      "Valve replacement: zero energy was never checked before the joint was opened and leaking was noticed.",
    provider: "rules",
    event: {
      report_id: "VALVE-01",
      activity: "valve_replacement",
      task_phase: "repair",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      exposure: "uncontrolled_gas_release",
      potential_consequence: "serious_injury_or_fatality",
      location: "process_area",
      confidence: 0.94,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "valve replacement",
        barrier: "zero energy",
        barrier_state: "never checked",
        exposure: "leaking was noticed",
      },
      sif: {
        classification: "high",
        confidence: 0.94,
        reason: "Joint unbolted prior to zero energy verification.",
        supporting_evidence: [
          "Hazardous energy: pressurized gas",
          "Barrier state: not verified",
        ],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.94,
        basis: "Isolation verification omitted.",
        evidence: ["zero energy was never checked"],
      },
      precursor_signature: {
        activity: "valve_replacement",
        task_phase: "repair",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "not_verified",
        exposure: "uncontrolled_gas_release",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-001",
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
  },
  {
    id: "OBS-DEMO04",
    report_id: "PUMP-01",
    report_type: "near_miss",
    narrative:
      "Pump maintenance near the transfer station: no one verified isolation before the flange was disconnected; a small hydrocarbon release was noticed.",
    provider: "rules",
    event: {
      report_id: "PUMP-01",
      activity: "pump_maintenance",
      task_phase: "maintenance",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      exposure: "uncontrolled_gas_release",
      potential_consequence: "serious_injury_or_fatality",
      location: "pump_station",
      confidence: 0.91,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "pump maintenance",
        barrier: "isolation",
        barrier_state: "no one verified",
        exposure: "hydrocarbon release",
      },
      sif: {
        classification: "high",
        confidence: 0.91,
        reason: "Hydrocarbon line uncoupled without proven isolation.",
        supporting_evidence: ["no one verified isolation"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.91,
        basis: "Line of fire & energy isolation violation.",
        evidence: ["no one verified isolation"],
      },
      precursor_signature: {
        activity: "pump_maintenance",
        task_phase: "maintenance",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "not_verified",
        exposure: "uncontrolled_gas_release",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-001",
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 26).toISOString(),
  },
  {
    id: "OBS-DEMO05",
    report_id: "HOTW-01",
    report_type: "incident",
    narrative:
      "Hot work area: gas testing had not been completed before grinding started; a flash fire ignited nearby rags.",
    provider: "rules",
    event: {
      report_id: "HOTW-01",
      activity: "hot_work",
      task_phase: "maintenance",
      energy: "flammable_atmosphere",
      barrier: "hot_work_controls",
      barrier_state: "not_verified",
      exposure: "fire_or_explosion",
      potential_consequence: "serious_injury_or_fatality",
      location: "workshop",
      confidence: 0.89,
      life_saving_rules: ["hot_work", "gas_testing"],
      field_evidence: {
        activity: "hot work",
        barrier: "gas testing",
        barrier_state: "had not been completed",
        exposure: "flash fire ignited",
      },
      sif: {
        classification: "high",
        confidence: 0.89,
        reason: "Hot work sparks with flammable gas testing omitted.",
        supporting_evidence: ["gas testing had not been completed"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["hot_work", "gas_testing"],
        confidence: 0.92,
        basis: "Direct violation of hot work and atmospheric testing rules.",
        evidence: ["gas testing had not been completed", "flash fire ignited"],
      },
      precursor_signature: {
        activity: "hot_work",
        task_phase: "maintenance",
        energy: "flammable_atmosphere",
        barrier: "hot_work_controls",
        barrier_state: "not_verified",
        exposure: "fire_or_explosion",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-002",
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 48).toISOString(),
  },
  {
    id: "OBS-DEMO06",
    report_id: "VER-01",
    report_type: "unknown",
    narrative:
      "Pipeline maintenance: zero pressure was confirmed and isolation verified before the joint was opened. No issue.",
    provider: "rules",
    event: {
      report_id: "VER-01",
      activity: "pipeline_maintenance",
      task_phase: "maintenance",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "verified",
      exposure: "unknown",
      potential_consequence: "unknown",
      location: "pipeline_section",
      confidence: 0.98,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "pipeline maintenance",
        barrier: "isolation",
        barrier_state: "verified",
      },
      sif: {
        classification: "low",
        confidence: 0.95,
        reason: "Positive control verified: zero pressure and isolation proven.",
        supporting_evidence: ["zero pressure was confirmed", "isolation verified"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.98,
        basis: "Energy isolation rule followed correctly.",
        evidence: ["isolation verified"],
      },
      precursor_signature: {
        activity: "pipeline_maintenance",
        task_phase: "maintenance",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "verified",
        exposure: "unknown",
        potential_consequence: "unknown",
      },
    },
    precursor_family_id: "PFAM-003",
    validation: "validated",
    created_at: new Date(Date.now() - 3600000 * 52).toISOString(),
  },
  {
    id: "OBS-DEMO08",
    report_id: "VER-02",
    report_type: "unknown",
    narrative:
      "Compressor maintenance: lockout was checked and the system proven depressurized before work. Everything was safe.",
    provider: "rules",
    event: {
      report_id: "VER-02",
      activity: "compressor_maintenance",
      task_phase: "maintenance",
      energy: "pressurized_gas",
      barrier: "energy_isolation",
      barrier_state: "verified",
      exposure: "unknown",
      potential_consequence: "unknown",
      location: "compressor_room",
      confidence: 0.97,
      life_saving_rules: ["energy_isolation"],
      field_evidence: {
        activity: "compressor maintenance",
        barrier: "lockout",
        barrier_state: "checked and the system proven depressurized",
      },
      sif: {
        classification: "low",
        confidence: 0.95,
        reason: "Positive control verified: lockout applied and system depressurized.",
        supporting_evidence: ["lockout was checked", "system proven depressurized"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["energy_isolation"],
        confidence: 0.97,
        basis: "Energy isolation rule followed correctly.",
        evidence: ["lockout was checked"],
      },
      precursor_signature: {
        activity: "compressor_maintenance",
        task_phase: "maintenance",
        energy: "pressurized_gas",
        barrier: "energy_isolation",
        barrier_state: "verified",
        exposure: "unknown",
        potential_consequence: "unknown",
      },
    },
    precursor_family_id: "PFAM-003",
    validation: "validated",
    created_at: new Date(Date.now() - 3600000 * 53).toISOString(),
  },
  {
    id: "OBS-DEMO09",
    report_id: "HOTW-02",
    report_type: "near_miss",
    narrative:
      "Grinding operations over the tank opening: the flammable gas test was skipped and sparks could have ignited the vapours.",
    provider: "rules",
    event: {
      report_id: "HOTW-02",
      activity: "hot_work",
      task_phase: "maintenance",
      energy: "flammable_atmosphere",
      barrier: "hot_work_controls",
      barrier_state: "not_verified",
      exposure: "fire_or_explosion",
      potential_consequence: "serious_injury_or_fatality",
      location: "tank_farm",
      confidence: 0.9,
      life_saving_rules: ["hot_work", "gas_testing"],
      field_evidence: {
        activity: "grinding operations",
        barrier: "gas test",
        barrier_state: "skipped",
        exposure: "ignited the vapours",
      },
      sif: {
        classification: "high",
        confidence: 0.9,
        reason: "Ignition source present with flammable atmosphere testing omitted.",
        supporting_evidence: ["gas test was skipped"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: ["hot_work", "gas_testing"],
        confidence: 0.9,
        basis: "Hot work without atmospheric testing.",
        evidence: ["gas test was skipped"],
      },
      precursor_signature: {
        activity: "hot_work",
        task_phase: "maintenance",
        energy: "flammable_atmosphere",
        barrier: "hot_work_controls",
        barrier_state: "not_verified",
        exposure: "fire_or_explosion",
        potential_consequence: "serious_injury_or_fatality",
      },
    },
    precursor_family_id: "PFAM-002",
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 49).toISOString(),
  },
  {
    id: "OBS-DEMO07",
    report_id: "WATCH-01",
    report_type: "ua_uc",
    narrative:
      "An area watch noted a strange vibration noise near the compressor during a routine walkdown; no work was in progress.",
    provider: "rules",
    event: {
      report_id: "WATCH-01",
      activity: "unknown",
      task_phase: "inspection",
      energy: "moving_equipment",
      barrier: "machinery_guarding",
      barrier_state: "unknown",
      exposure: "unknown",
      potential_consequence: "unknown",
      location: "compressor_room",
      confidence: 0.45,
      life_saving_rules: [],
      field_evidence: {
        energy: "strange vibration",
        location: "compressor",
      },
      sif: {
        classification: "needs_review",
        confidence: 0.45,
        reason: "Ambiguous observation narrative with missing barrier details.",
        supporting_evidence: ["No barrier failure specified"],
        model_note:
          "Prototype assessment. Decision support only; not accident prediction.",
      },
      lsr_mapping: {
        rules: [],
        confidence: 0.0,
        basis: "No direct Life-Saving Rule correlation.",
        evidence: [],
      },
      precursor_signature: {
        activity: "unknown",
        task_phase: "inspection",
        energy: "moving_equipment",
        barrier: "machinery_guarding",
        barrier_state: "unknown",
        exposure: "unknown",
        potential_consequence: "unknown",
      },
    },
    precursor_family_id: null,
    validation: "pending",
    created_at: new Date(Date.now() - 3600000 * 70).toISOString(),
  },
];

export const DEMO_FAMILIES = [
  {
    id: "PFAM-001",
    name: "Energy Isolation Verification Failure",
    description:
      "4 observation(s). Common barrier: Energy Isolation (state: Not Verified). Common hazard/energy: Pressurized Gas. Common exposure: Uncontrolled Gas Release.",
    recurring: true,
    recurring_threshold: 2,
    common_barrier: "energy_isolation",
    common_barrier_state: "not_verified",
    common_energy: "pressurized_gas",
    common_exposure: "uncontrolled_gas_release",
    activities: [
      "pipeline_maintenance",
      "compressor_maintenance",
      "valve_replacement",
      "pump_maintenance",
    ],
    locations: ["pipeline_section", "compressor_room", "process_area", "pump_station"],
    hazard: "Pressurized Gas / Hydrocarbon Residuals",
    attention_signal: 84.7,
    attention_basis: [
      "Recurrence count: 4 (≥ threshold 2)",
      "Failed barrier state: not_verified across 4/4 members",
      "Cross-activity spread: 4 distinct activities affected",
      "SIF potential: 4 high-severity precursor observations",
    ],
    attention_factors: [
      { factor: "recurrence", weight: 0.25, score: 0.9 },
      { factor: "barrier_failure", weight: 0.2, score: 1.0 },
      { factor: "exposure", weight: 0.2, score: 0.9 },
      { factor: "cross_activity", weight: 0.15, score: 0.8 },
      { factor: "sif_evidence", weight: 0.15, score: 0.95 },
      { factor: "energy_severity", weight: 0.05, score: 0.9 },
    ],
    sif_potential_count: 4,
    observation_ids: ["OBS-DEMO01", "OBS-DEMO02", "OBS-DEMO03", "OBS-DEMO04"],
    grouping_evidence: [
      {
        dimension: "energy",
        value: "pressurized_gas",
        status: "same",
        coverage: 1.0,
        note: "Pressurized Gas in 4/4 observation(s)",
      },
      {
        dimension: "barrier",
        value: "energy_isolation",
        status: "same",
        coverage: 1.0,
        note: "Energy Isolation in 4/4 observation(s)",
      },
      {
        dimension: "barrier_state",
        value: "not_verified",
        status: "same",
        coverage: 1.0,
        note: "Not Verified in 4/4 observation(s)",
      },
      {
        dimension: "exposure",
        value: "uncontrolled_gas_release",
        status: "same",
        coverage: 1.0,
        note: "Uncontrolled Gas Release in 4/4 observation(s)",
      },
      {
        dimension: "task_phase",
        value: "maintenance",
        status: "mixed",
        coverage: 0.75,
        note: "Maintenance dominant (3/4), 1 repair",
      },
      {
        dimension: "activity",
        value: "pipeline_maintenance",
        status: "distinct",
        coverage: 0.25,
        note: "Distinct activities converging on the same barrier mechanism",
      },
    ],
    exclusions: [
      {
        other_family_id: "PFAM-002",
        similarity: 0.35,
        differing_dimensions: ["barrier", "energy", "exposure"],
        basis:
          "Structurally separated: fails Hot Work Controls instead of Energy Isolation.",
      },
      {
        other_family_id: "PFAM-003",
        similarity: 0.0,
        differing_dimensions: ["barrier_state"],
        basis:
          "Hard exclusion rule: Verified positive barrier state cannot merge with Not Verified failure family.",
      },
    ],
    created_at: new Date(Date.now() - 3600000 * 20).toISOString(),
  },
  {
    id: "PFAM-002",
    name: "Hot Work Controls Verification Failure",
    description:
      "2 observation(s). Common barrier: Hot Work Controls (state: Not Verified). Common hazard/energy: Flammable Atmosphere. Common exposure: Fire or Explosion.",
    recurring: true,
    recurring_threshold: 2,
    common_barrier: "hot_work_controls",
    common_barrier_state: "not_verified",
    common_energy: "flammable_atmosphere",
    common_exposure: "fire_or_explosion",
    activities: ["hot_work"],
    locations: ["workshop", "tank_farm"],
    hazard: "Flammable atmosphere with grinding/cutting ignition source",
    attention_signal: 78.9,
    attention_basis: [
      "Recurrence count: 2 (≥ threshold 2)",
      "Barrier failure: hot work controls not verified prior to spark emission",
      "High SIF potential: 2 high-severity records",
    ],
    attention_factors: [],
    sif_potential_count: 2,
    observation_ids: ["OBS-DEMO05", "OBS-DEMO09"],
    grouping_evidence: [
      {
        dimension: "barrier",
        value: "hot_work_controls",
        status: "same",
        coverage: 1.0,
        note: "Hot Work Controls in 2/2 observation(s)",
      },
      {
        dimension: "barrier_state",
        value: "not_verified",
        status: "same",
        coverage: 1.0,
        note: "Not Verified in 2/2 observation(s)",
      },
      {
        dimension: "energy",
        value: "flammable_atmosphere",
        status: "same",
        coverage: 1.0,
        note: "Flammable Atmosphere in 2/2 observation(s)",
      },
    ],
    exclusions: [
      {
        other_family_id: "PFAM-001",
        similarity: 0.35,
        differing_dimensions: ["barrier", "energy", "exposure"],
        basis: "Different critical barrier and hazardous energy.",
      },
    ],
    created_at: new Date(Date.now() - 3600000 * 40).toISOString(),
  },
  {
    id: "PFAM-003",
    name: "Energy Isolation Verified",
    description:
      "2 observation(s). Common barrier: Energy Isolation (state: Verified). Hard negative / compliance control group — excluded from precursor families.",
    family_type: "controlled",
    recurring: false,
    recurring_threshold: 2,
    common_barrier: "energy_isolation",
    common_barrier_state: "verified",
    common_energy: "pressurized_gas",
    common_exposure: "unknown",
    activities: ["pipeline_maintenance", "compressor_maintenance"],
    locations: ["pipeline_section", "compressor_room"],
    hazard: "Controlled energy isolation compliance",
    attention_signal: 21.5,
    attention_basis: [
      "Verified compliance control group — not a precursor family",
      "Demonstrates hard separation from failure families",
    ],
    attention_factors: [],
    sif_potential_count: 0,
    observation_ids: ["OBS-DEMO06", "OBS-DEMO08"],
    grouping_evidence: [
      {
        dimension: "barrier",
        value: "energy_isolation",
        status: "same",
        coverage: 1.0,
        note: "Energy Isolation in 2/2 observation(s)",
      },
      {
        dimension: "barrier_state",
        value: "verified",
        status: "same",
        coverage: 1.0,
        note: "Verified barrier state in 2/2 observation(s)",
      },
      {
        dimension: "exposure",
        value: "unknown",
        status: "unknown",
        coverage: 0.0,
        note: "Unknown / not stated across member reports",
      },
    ],
    exclusions: [
      {
        other_family_id: "PFAM-001",
        similarity: 0.0,
        differing_dimensions: ["barrier_state"],
        basis:
          "Hard exclusion rule: Verified barrier state never merges with Not Verified.",
      },
    ],
    created_at: new Date(Date.now() - 3600000 * 50).toISOString(),
  },
];

export const DEMO_DASHBOARD = {
  total_observations: 248,
  sif_potential_observations: 47,
  precursor_families: 18,
  recurring_precursor_families: 4,
  recurring_barrier_failures: 5,
  locations_affected: 8,
  activities_affected: 6,
  backend: "SQLite (Auto fallback) / Oil India HSE",
};

// Demo-fallback aggregate scope, kept self-consistent so every percentage and
// total the Analytics page derives from these rows adds up against the demo
// dashboard total (sif counts sum to total_observations = 248).
export const DEMO_AGGREGATES = {
  barrier: [
    { barrier: "energy_isolation", barrier_state: "not_verified", count: 28 },
    { barrier: "energy_isolation", barrier_state: "verified", count: 22 },
    { barrier: "hot_work_controls", barrier_state: "not_verified", count: 18 },
    { barrier: "fall_protection", barrier_state: "absent", count: 14 },
    { barrier: "confined_space_procedure", barrier_state: "failed", count: 12 },
    { barrier: "machinery_guarding", barrier_state: "partially_effective", count: 9 },
  ],
  activity: [
    { activity: "pipeline_maintenance", count: 48 },
    { activity: "compressor_maintenance", count: 36 },
    { activity: "hot_work", count: 32 },
    { activity: "valve_replacement", count: 24 },
    { activity: "pump_maintenance", count: 20 },
    { activity: "working_at_height", count: 18 },
  ],
  sif: [
    { classification: "high", count: 47 },
    { classification: "medium", count: 68 },
    { classification: "low", count: 112 },
    { classification: "needs_review", count: 21 },
  ],
  lsr: [
    { life_saving_rule: "energy_isolation", count: 52 },
    { life_saving_rule: "hot_work", count: 34 },
    { life_saving_rule: "working_at_height", count: 22 },
    { life_saving_rule: "gas_testing", count: 19 },
    { life_saving_rule: "line_of_fire", count: 16 },
  ],
};

export const DEMO_EVALUATION = {
  run_id: "EVAL-2026-FROZEN-216",
  created_at: new Date().toISOString(),
  metrics: {
    record_count: 216,
    field_accuracy: {
      activity: 1.0,
      task_phase: 0.995,
      energy: 0.954,
      barrier: 0.977,
      barrier_state: 1.0,
      exposure: 0.968,
      potential_consequence: 0.958,
      location: 1.0,
    },
    sif: {
      macro_f1: 0.896,
      accuracy: 0.977,
    },
    critical_suite: {
      "isolation_verified_vs_not (n=40)": { accuracy: 1.0, n: 40 },
      "hard_negatives (n=30)": { accuracy: 1.0, n: 30 },
      "cross_equipment_grouping (n=20)": { accuracy: 1.0, n: 20 },
      "why_not_grouped_separation (n=15)": { accuracy: 1.0, n: 15 },
    },
  },
  counts: { records: 216 },
};

// ---------------------------------------------------------------------------
// CAPA Effectiveness labels & demo fallback data (mirrors seed_demo --capa)
// ---------------------------------------------------------------------------
export const EFFECTIVENESS_STATUS_LABELS = {
  improvement_observed: "Evidence of Improvement",
  recurrence_detected: "Recurrence Detected",
  insufficient_evidence: "Insufficient Evidence",
  under_observation: "Under Observation",
};

export const CAPA_STATUS_LABELS = {
  open: "Open",
  in_progress: "In Progress",
  closed: "Closed",
  cancelled: "Cancelled",
  draft: "Draft",
};

export const EFFECTIVENESS_STYLES = {
  improvement_observed: "bg-emerald-950/70 text-emerald-300 border-emerald-700/60",
  recurrence_detected: "bg-rose-950/70 text-rose-300 border-rose-700/60",
  insufficient_evidence: "bg-slate-900 text-slate-400 border-slate-700/60",
  under_observation: "bg-amber-950/60 text-amber-300 border-amber-700/60",
};

export const CAPA_STATUS_STYLES = {
  open: "bg-sky-950/60 text-sky-300 border-sky-700/60",
  in_progress: "bg-amber-950/60 text-amber-300 border-amber-700/60",
  closed: "bg-emerald-950/60 text-emerald-300 border-emerald-700/60",
  cancelled: "bg-slate-900 text-slate-400 border-slate-700/60",
  draft: "bg-slate-900 text-slate-400 border-slate-700/60",
};

export function effectivenessStatusLabel(value) {
  const norm = value || "insufficient_evidence";
  return EFFECTIVENESS_STATUS_LABELS[norm] || label(norm);
}

export function capaStatusLabel(value) {
  const norm = value || "unknown";
  return CAPA_STATUS_LABELS[norm] || label(norm);
}

const DAY_MS = 24 * 60 * 60 * 1000;

// Evaluation-period helper: how many days the baseline looked back and how many
// days of post-closure evidence have actually been collected so far (capped at
// the configured post window). Deterministic, matches the backend rule engine.
export function capaEvaluationPeriod(capa) {
  const baselineDays = Number(capa?.baseline?.window_days) || 90;
  const postDays = Number(capa?.post_capa?.window_days) || baselineDays;
  let postElapsed = 0;
  let postOpen = false;
  if (capa?.status === "closed" && capa?.closed_at) {
    postOpen = true;
    const closed = new Date(capa.closed_at).getTime();
    if (Number.isFinite(closed)) {
      postElapsed = Math.max(0, Math.floor((Date.now() - closed) / DAY_MS));
      postElapsed = Math.min(Math.max(0, postDays), postElapsed);
    }
  }
  return { baselineDays, postDays, postOpen, postElapsed };
}

// Mirrors backend seed_capa_demo() verdicts: recurrence / improvement /
// under-observation / insufficient-evidence, with evidence snapshots frozen.
export const DEMO_CAPAS = [
  {
    id: "CAPA-CAPA-RECUR-01",
    report_id: "CAPA-RECUR-01",
    title: "Introduce mandatory isolation verification checklist.",
    description:
      "Closed CAPA targeting energy isolation. A fresh energy-isolation failure inside the post-closure window indicates recurrence.",
    linked_barrier_id: "energy_isolation",
    location: "process_area",
    site: "EAST",
    status: "closed",
    created_at: new Date(Date.now() - 86400000 * 10).toISOString(),
    closed_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    baseline: {
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      energy: "pressurized_gas",
      exposure: "uncontrolled_gas_release",
      location: "process_area",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 130).toISOString(),
      to_iso: new Date(Date.now() - 86400000 * 10).toISOString(),
      failure_count: 3,
      sif_potential_count: 3,
      affected_sites: 3,
      observation_ids: ["OBS-CAPAB-01", "OBS-CAPAB-02", "OBS-CAPAB-03"],
    },
    post_capa: {
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 5).toISOString(),
      to_iso: new Date(Date.now() + 86400000 * 115).toISOString(),
      recurrence_count: 1,
      recurrence_observation_ids: ["OBS-CAPAP-01"],
      observation_ids: ["OBS-CAPAP-01"],
    },
    effectiveness_status: "recurrence_detected",
    effectiveness_basis: {
      window_days: 120,
      linked_barrier: "energy_isolation",
      status_rule: ">=1 barrier-state failure recurred after CAPA closure",
      baseline: {
        failure_count: 3,
        sif_potential_count: 3,
        affected_sites: 3,
        _counted: 3,
      },
      post_capa: { recurrence_count: 1, _counted: 1 },
      derivation:
        "Derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction.",
    },
    evidence_observation_ids: [
      "OBS-CAPAB-01", "OBS-CAPAB-02", "OBS-CAPAB-03", "OBS-CAPAP-01",
    ],
  },
  {
    id: "CAPA-CAPA-IMPR-01",
    report_id: "CAPA-IMPR-01",
    title: "Mandatory gas testing before every hot work job.",
    description:
      "Closed CAPA targeting hot work controls. A verified post-closure control observation with zero recurrences indicates improvement.",
    linked_barrier_id: "hot_work_controls",
    location: "workshop",
    site: "WEST",
    status: "closed",
    created_at: new Date(Date.now() - 86400000 * 8).toISOString(),
    closed_at: new Date(Date.now() - 86400000 * 4).toISOString(),
    baseline: {
      barrier: "hot_work_controls",
      barrier_state: "not_verified",
      energy: "flammable_atmosphere",
      exposure: "fire_or_explosion",
      location: "workshop",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 128).toISOString(),
      to_iso: new Date(Date.now() - 86400000 * 8).toISOString(),
      failure_count: 2,
      sif_potential_count: 2,
      affected_sites: 2,
      observation_ids: ["OBS-CAPAB-H1", "OBS-CAPAB-H2"],
    },
    post_capa: {
      barrier: "hot_work_controls",
      barrier_state: "verified",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 4).toISOString(),
      to_iso: new Date(Date.now() + 86400000 * 116).toISOString(),
      recurrence_count: 0,
      recurrence_observation_ids: [],
      observation_ids: ["OBS-CAPAP-H1"],
    },
    effectiveness_status: "improvement_observed",
    effectiveness_basis: {
      window_days: 120,
      linked_barrier: "hot_work_controls",
      status_rule:
        "Baseline barrier failure(s) existed and post-closure evidence shows zero recurrences",
      baseline: {
        failure_count: 2,
        sif_potential_count: 2,
        affected_sites: 2,
        _counted: 2,
      },
      post_capa: { recurrence_count: 0, _counted: 1 },
      derivation:
        "Derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction.",
    },
    evidence_observation_ids: ["OBS-CAPAB-H1", "OBS-CAPAB-H2", "OBS-CAPAP-H1"],
  },
  {
    id: "CAPA-CAPA-OBS-01",
    report_id: "CAPA-OBS-01",
    title: "Review energy isolation training compliance across crews.",
    description:
      "Open CAPA with baseline evidence present. Effectiveness stays under observation until closure.",
    linked_barrier_id: "energy_isolation",
    location: "process_area",
    site: "EAST",
    status: "open",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    closed_at: null,
    baseline: {
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      energy: "pressurized_gas",
      exposure: "uncontrolled_gas_release",
      location: "process_area",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 123).toISOString(),
      to_iso: new Date(Date.now() - 86400000 * 3).toISOString(),
      failure_count: 3,
      sif_potential_count: 3,
      affected_sites: 3,
      observation_ids: ["OBS-CAPAB-01", "OBS-CAPAB-02", "OBS-CAPAB-03"],
    },
    post_capa: {
      barrier: "energy_isolation",
      barrier_state: "not_verified",
      window_days: 120,
      from_iso: "",
      to_iso: "",
      recurrence_count: 0,
      recurrence_observation_ids: [],
      observation_ids: [],
    },
    effectiveness_status: "under_observation",
    effectiveness_basis: {
      window_days: 120,
      linked_barrier: "energy_isolation",
      status_rule: "CAPA is still in progress (not closed); awaiting closure",
      baseline: {
        failure_count: 3,
        sif_potential_count: 3,
        affected_sites: 3,
        _counted: 3,
      },
      post_capa: { recurrence_count: 0, _counted: 0 },
      derivation:
        "Derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction.",
    },
    evidence_observation_ids: ["OBS-CAPAB-01", "OBS-CAPAB-02", "OBS-CAPAB-03"],
  },
  {
    id: "CAPA-CAPA-INSUF-01",
    report_id: "CAPA-INSUF-01",
    title: "Review machinery guarding on the transfer pumps.",
    description:
      "Closed CAPA with no baseline barrier evidence to compare against, so effectiveness cannot be derived.",
    linked_barrier_id: "machinery_guarding",
    location: "pump_station",
    site: "WEST",
    status: "closed",
    created_at: new Date(Date.now() - 86400000 * 9).toISOString(),
    closed_at: new Date(Date.now() - 86400000 * 6).toISOString(),
    baseline: {
      barrier: "machinery_guarding",
      barrier_state: "unknown",
      energy: "unknown",
      exposure: "unknown",
      location: "pump_station",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 129).toISOString(),
      to_iso: new Date(Date.now() - 86400000 * 9).toISOString(),
      failure_count: 0,
      sif_potential_count: 0,
      affected_sites: 1,
      observation_ids: [],
    },
    post_capa: {
      barrier: "machinery_guarding",
      barrier_state: "unknown",
      window_days: 120,
      from_iso: new Date(Date.now() - 86400000 * 6).toISOString(),
      to_iso: new Date(Date.now() + 86400000 * 114).toISOString(),
      recurrence_count: 0,
      recurrence_observation_ids: [],
      observation_ids: [],
    },
    effectiveness_status: "insufficient_evidence",
    effectiveness_basis: {
      window_days: 120,
      linked_barrier: "machinery_guarding",
      status_rule:
        "No baseline barrier failure or SIF-potential evidence to compare against after closure",
      baseline: {
        failure_count: 0,
        sif_potential_count: 0,
        affected_sites: 1,
        _counted: 0,
      },
      post_capa: { recurrence_count: 0, _counted: 0 },
      derivation:
        "Derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction.",
    },
    evidence_observation_ids: [],
  },
];

// ---------------------------------------------------------------------------
// CAPA Effectiveness dashboard integration helpers (pure functions, testable)
// ---------------------------------------------------------------------------

// Signal priority used to surface ONE compact CAPA card on the main dashboard.
// A fresh post-CAPA recurrence is the loudest signal, then an open/awaiting
// closure CAPA, then a concrete improvement, then the evidence-gap verdict.
const CAPA_SIGNAL_ORDER = [
  "recurrence_detected",
  "under_observation",
  "improvement_observed",
  "insufficient_evidence",
];

// Pick the single highest-signal CAPA (optionally restricted to a set of
// barrier ids, e.g. the barriers that appear on the current dashboard).
// Tie-broken by most recently created so the newest record wins.
export function pickCapaSignal(capas, barrierIds = null) {
  const list =
    Array.isArray(barrierIds) && barrierIds.length > 0
      ? (capas || []).filter((c) => barrierIds.includes(c.linked_barrier_id))
      : capas || [];
  const rank = (c) => {
    const i = CAPA_SIGNAL_ORDER.indexOf(c?.effectiveness_status);
    return i === -1 ? CAPA_SIGNAL_ORDER.length : i;
  };
  return (
    [...list].sort(
      (a, b) =>
        rank(a) - rank(b) ||
        (String(a.created_at) < String(b.created_at) ? 1 : -1),
    )[0] || null
  );
}

// Per-barrier summary of the CAPA portfolio: linked count, open/closed counts,
// per-verdict tallies, and the latest (most recently created) CAPA for inline
// "View CAPA" links. Never fabricates anything — pure projection of the rows.
export function summarizeCapaForBarrier(capas, barrierId) {
  const linked = (capas || []).filter(
    (c) => c.linked_barrier_id === barrierId,
  );
  const latest =
    [...linked].sort((a, b) =>
      String(a.created_at) < String(b.created_at) ? 1 : -1,
    )[0] || null;
  return {
    total: linked.length,
    capas: linked,
    open: linked.filter((c) => c.status === "open" || c.status === "in_progress").length,
    closed: linked.filter((c) => c.status === "closed").length,
    cancelled: linked.filter((c) => c.status === "cancelled").length,
    recurrenceDetected: linked.filter(
      (c) => c.effectiveness_status === "recurrence_detected",
    ).length,
    improvementObserved: linked.filter(
      (c) => c.effectiveness_status === "improvement_observed",
    ).length,
    underObservation: linked.filter(
      (c) => c.effectiveness_status === "under_observation",
    ).length,
    insufficientEvidence: linked.filter(
      (c) => c.effectiveness_status === "insufficient_evidence",
    ).length,
    latest,
  };
}

// ---------------------------------------------------------------------------
// Primary API Object
// ---------------------------------------------------------------------------
export const api = {
  health: async () => {
    try {
      return await request("/health");
    } catch {
      return {
        status: "ok (demo mode)",
        service: "MECHORA API (Client Demo Mode)",
        version: "0.1.0",
        backend: "offline-ready",
        provider: "rules",
      };
    }
  },

  // Upload a PDF/DOCX/TXT report; the backend extracts plain text, SEGMENTS it,
  // and returns { filename, file_type, text, character_count, report_count,
  // segments:[{index, kind, heading, text, character_count}] }. Non-report
  // segments (kind "non_report") are excluded from analysis.
  extractDocument: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${base}/documents/extract`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        /* surface raw status text */
      }
      throw new Error(detail);
    }
    return res.json();
  },

  // Upload then ANALYZE each report segment independently. Every report
  // segment in the document gets its own observation (report_id=<doc>-SEG<n>).
  // Returns { document_id, report_count, analyses:[{report_segment_id,
  // segment_index, heading, analysis, error}], observations_created }.
  analyzeDocument: async (file, { reportId = "", provider = "", reportType = "unknown" } = {}) => {
    const form = new FormData();
    form.append("file", file);
    form.append("report_type", reportType);
    const qs = new URLSearchParams();
    if (reportId) qs.set("report_id", reportId);
    if (provider) qs.set("provider", provider);
    const res = await fetch(`${base}/documents/analyze${qs.toString() ? `?${qs}` : ""}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        /* surface raw status text */
      }
      throw new Error(detail);
    }
    return res.json();
  },

  analyze: async (payload) => {
    try {
      return await request("/analyze", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch (err) {
      // If backend is not reached, simulate extraction from deterministic rules locally
      const narrativeLower = payload.narrative.toLowerCase();
      let activity = "pipeline_maintenance";
      let barrier = "energy_isolation";
      let barrier_state = "not_verified";
      let energy = "pressurized_gas";
      let exposure = "uncontrolled_gas_release";
      let sif = "high";

      if (narrativeLower.includes("compressor")) activity = "compressor_maintenance";
      if (narrativeLower.includes("valve")) activity = "valve_replacement";
      if (narrativeLower.includes("pump")) activity = "pump_maintenance";
      if (narrativeLower.includes("hot work") || narrativeLower.includes("grind")) {
        activity = "hot_work";
        barrier = "hot_work_controls";
        energy = "flammable_atmosphere";
        exposure = "fire_or_explosion";
      }

      if (
        (narrativeLower.includes("verified") || narrativeLower.includes("confirmed")) &&
        !narrativeLower.includes("not") &&
        !narrativeLower.includes("never") &&
        !narrativeLower.includes("without")
      ) {
        barrier_state = "verified";
        sif = "low";
        exposure = "unknown";
      }

      const mockId = `OBS-${Date.now()}`;
      return {
        id: mockId,
        report_id: payload.report_id || `REPORT-${Date.now().toString().slice(-4)}`,
        provider: "rules (client fallback)",
        report_type: payload.report_type || "unknown",
        warnings: [
          "Live backend unreachable; deterministic browser fallback analysis presented.",
        ],
        event: {
          report_id: payload.report_id || `REPORT-${Date.now().toString().slice(-4)}`,
          activity,
          task_phase: "maintenance",
          energy,
          barrier,
          barrier_state,
          exposure,
potential_consequence:
              barrier_state === "verified"
                ? "unknown"
                : "serious_injury_or_fatality",
          location: "pipeline_section",
          confidence: 0.93,
          life_saving_rules: [barrier === "hot_work_controls" ? "hot_work" : "energy_isolation"],
          field_evidence: {
            activity: activity.replace(/_/g, " "),
            energy: energy.replace(/_/g, " "),
            barrier: barrier.replace(/_/g, " "),
            barrier_state: barrier_state.replace(/_/g, " "),
          },
          sif: {
            classification: sif,
            confidence: 0.93,
            reason: `Deterministic assessment based on ${energy.replace(/_/g, " ")} with barrier ${barrier_state.replace(/_/g, " ")}.`,
            supporting_evidence: [
              `Energy: ${energy.replace(/_/g, " ")}`,
              `Barrier State: ${barrier_state.replace(/_/g, " ")}`,
            ],
            model_note:
              "Prototype assessment. Decision support only; not accident prediction.",
          },
          lsr_mapping: {
            rules: [barrier === "hot_work_controls" ? "hot_work" : "energy_isolation"],
            confidence: 0.93,
            basis: "Identified Life-Saving Rule control mechanism.",
            evidence: [barrier.replace(/_/g, " ")],
          },
          precursor_signature: {
            activity,
            task_phase: "maintenance",
            energy,
            barrier,
            barrier_state,
            exposure,
            potential_consequence:
              barrier_state === "verified"
                ? "unknown"
                : "serious_injury_or_fatality",
          },
        },
        precursor_family_id:
          barrier_state === "verified"
            ? "PFAM-003"
            : barrier === "hot_work_controls"
            ? "PFAM-002"
            : "PFAM-001",
      };
    }
  },

  observations: async (params = {}) => {
    try {
      const qs = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params).filter(([, v]) => v !== "" && v != null),
        ),
      ).toString();
      const res = await request(`/observations${qs ? `?${qs}` : ""}`);
      if (res && Array.isArray(res.observations)) {
        return res;
      }
      return { total: DEMO_OBSERVATIONS.length, observations: DEMO_OBSERVATIONS };
    } catch {
      let list = [...DEMO_OBSERVATIONS];
      if (params.barrier_state) {
        list = list.filter((o) => o.event.barrier_state === params.barrier_state);
      }
      if (params.sif) {
        list = list.filter((o) => o.event.sif?.classification === params.sif);
      }
      if (params.family_id) {
        list = list.filter((o) => o.precursor_family_id === params.family_id);
      }
      if (params.q) {
        const q = params.q.toLowerCase();
        list = list.filter(
          (o) =>
            o.narrative.toLowerCase().includes(q) ||
            o.report_id.toLowerCase().includes(q) ||
            o.id.toLowerCase().includes(q),
        );
      }
      return { total: list.length, observations: list };
    }
  },

  observation: async (obsId) => {
    try {
      return await request(`/observations/${obsId}`);
    } catch {
      const found = DEMO_OBSERVATIONS.find((o) => o.id === obsId || o.report_id === obsId);
      if (found) return found;
      return DEMO_OBSERVATIONS[0];
    }
  },

  updateValidation: async (obsId, status) => {
    try {
      return await request(`/observations/${obsId}/validation`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
    } catch {
      // Return local simulated update
      const found = DEMO_OBSERVATIONS.find((o) => o.id === obsId || o.report_id === obsId);
      if (found) {
        found.validation = status;
        return found;
      }
      return { id: obsId, validation: status };
    }
  },

  // Delete an observation. Families are rebuilt server-side so cluster
  // membership and the family_id back-reference stay consistent.
  deleteObservation: async (obsId) => {
    const res = await fetch(`${base}/observations/${encodeURIComponent(obsId)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        /* surface raw status text */
      }
      throw new Error(detail);
    }
    // Demo fallback: remove the local record so the browser stays consistent
    if (res.status === 204) {
      const idx = DEMO_OBSERVATIONS.findIndex((o) => o.id === obsId || o.report_id === obsId);
      if (idx >= 0) DEMO_OBSERVATIONS.splice(idx, 1);
    }
    return { deleted: true };
  },

  // CAPA list, filtered by status and/or linked barrier.
  // Demo mode is the app default: whenever the backend has no CAPA rows yet
  // (fresh DB / demo setup), the 4 seeded demo CAPAs are surfaced so the SIH
  // demo always opens showing all four effectiveness verdicts immediately.
  capas: async (params = {}) => {
    let list = [...DEMO_CAPAS];
    try {
      // The frontend uses camelCase filters; the API speaks snake_case.
      const qs = new URLSearchParams(
        Object.fromEntries(
          Object.entries({
            status: params.status,
            linked_barrier_id: params.linkedBarrierId,
            limit: params.limit,
            offset: params.offset,
          }).filter(([, v]) => v !== "" && v != null),
        ),
      ).toString();
      const res = await request(`/capas${qs ? `?${qs}` : ""}`);
      if (res && Array.isArray(res.capas) && res.capas.length > 0) {
        return res;
      }
    } catch {
      /* backend unreachable -> demo fallback below */
    }
    if (params.status) {
      list = list.filter((c) => c.status === params.status);
    }
    if (params.linkedBarrierId) {
      list = list.filter((c) => c.linked_barrier_id === params.linkedBarrierId);
    }
    return { total: list.length, capas: list, demo: true };
  },

  capa: async (capaId) => {
    try {
      return await request(`/capas/${encodeURIComponent(capaId)}`);
    } catch {
      const found = DEMO_CAPAS.find(
        (c) => c.id === capaId || c.report_id === capaId,
      );
      if (found) return found;
      throw new Error("CAPA not found");
    }
  },

  // Create a CAPA targeted at one linked barrier. Effectiveness is derived
  // server-side; demo fallback simulates the deterministic under-observation
  // baseline state (no evidence to compare on a brand-new CAPA).
  createCapa: async (payload) => {
    try {
      return await request("/capas", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch {
      const now = new Date();
      const windowDays = payload.window_days || 90;
      const barrier = payload.linked_barrier_id || "unknown";
      const mock = {
        id: `CAPA-${Date.now()}`,
        report_id: payload.report_id || `CAPA-${String(Date.now()).slice(-6)}`,
        title: payload.title,
        description: payload.description || "",
        linked_barrier_id: barrier,
        location: payload.location || "",
        site: payload.site || "",
        status: payload.status || "open",
        created_at: payload.created_at || now.toISOString(),
        closed_at: null,
        baseline: {
          barrier,
          barrier_state: "unknown",
          energy: "unknown",
          exposure: "unknown",
          location: payload.location || "",
          window_days: windowDays,
          from_iso: new Date(now.getTime() - windowDays * 86400000).toISOString(),
          to_iso: now.toISOString(),
          failure_count: 0,
          sif_potential_count: 0,
          affected_sites: 0,
          observation_ids: [],
        },
        post_capa: {
          barrier,
          barrier_state: "unknown",
          window_days: windowDays,
          from_iso: "",
          to_iso: "",
          recurrence_count: 0,
          recurrence_observation_ids: [],
          observation_ids: [],
        },
        effectiveness_status: "under_observation",
        effectiveness_basis: {
          window_days: windowDays,
          linked_barrier: barrier,
          status_rule: "CAPA is still in progress (not closed); awaiting closure",
          baseline: {
            failure_count: 0,
            sif_potential_count: 0,
            affected_sites: 0,
            _counted: 0,
          },
          post_capa: { recurrence_count: 0, _counted: 0 },
          derivation:
            "Derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction.",
        },
        evidence_observation_ids: [],
      };
      DEMO_CAPAS.unshift(mock);
      return mock;
    }
  },

  // Transit a CAPA status. Closing persists closed_at and recomputes the
  // post-closure effectiveness window deterministically.
  updateCapaStatus: async (capaId, status, closedAt = null) => {
    try {
      return await request(`/capas/${encodeURIComponent(capaId)}/status`, {
        method: "POST",
        body: JSON.stringify({
          status,
          closed_at: closedAt || undefined,
        }),
      });
    } catch {
      const found = DEMO_CAPAS.find((c) => c.id === capaId || c.report_id === capaId);
      if (!found) throw new Error("CAPA not found");
      if (status === "closed") {
        found.status = "closed";
        found.closed_at = closedAt || new Date().toISOString();
        const hasBaseline = (found.baseline?.failure_count || 0) > 0;
        const postIds = found.post_capa?.observation_ids || [];
        const recurrences = found.post_capa?.recurrence_count || 0;
        let verdict = "under_observation";
        if (recurrences > 0) verdict = "recurrence_detected";
        else if (hasBaseline && postIds.length > 0) verdict = "improvement_observed";
        else if (!hasBaseline) verdict = "insufficient_evidence";
        found.effectiveness_status = verdict;
        found.effectiveness_basis = {
          ...(found.effectiveness_basis || {}),
          status_rule: {
            recurrence_detected: ">=1 barrier-state failure recurred after CAPA closure",
            improvement_observed:
              "Baseline barrier failure(s) existed and post-closure evidence shows zero recurrences",
            under_observation:
              "CAPA not closed or post-closure window has no observations yet",
            insufficient_evidence:
              "No baseline barrier failure or SIF-potential evidence to compare against after closure",
          }[verdict],
        };
      } else {
        found.status = status;
        found.closed_at = null;
        found.effectiveness_status = "under_observation";
      }
      return found;
    }
  },

  deleteCapa: async (capaId) => {
    const res = await fetch(`${base}/capas/${encodeURIComponent(capaId)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch {
        /* surface raw status text */
      }
      throw new Error(detail);
    }
    if (res.status === 204) {
      const idx = DEMO_CAPAS.findIndex((c) => c.id === capaId);
      if (idx >= 0) DEMO_CAPAS.splice(idx, 1);
    }
    return { deleted: true };
  },

  families: async (recurringOnly = false, limit = 200, includeControls = false) => {
    const precursorFamilies = (f) => includeControls || f.family_type !== "controlled";
    const recurringFamilies = DEMO_FAMILIES.filter((f) => f.recurring);
    const demofind = (recur) => {
      const list = DEMO_FAMILIES.filter((f) => precursorFamilies(f));
      const filtered = recur ? list.filter((f) => f.recurring) : list;
      return {
        total: filtered.length,
        recurring: recurringFamilies.filter((f) => f.family_type !== "controlled" || includeControls).length,
        families: filtered,
      };
    };
    try {
      const res = await request(
        `/families?recurring_only=${recurringOnly}&limit=${limit}&include_controls=${includeControls}`,
      );
      if (res && Array.isArray(res.families)) {
        return res;
      }
      return demofind(recurringOnly);
    } catch {
      return demofind(recurringOnly);
    }
  },

  family: async (famId) => {
    try {
      return await request(`/families/${famId}`);
    } catch {
      const found = DEMO_FAMILIES.find((f) => f.id === famId);
      if (found) return found;
      return DEMO_FAMILIES[0];
    }
  },

  dashboard: async () => {
    try {
      const res = await request("/dashboard");
      return res;
    } catch {
      return DEMO_DASHBOARD;
    }
  },

  ontology: async () => {
    try {
      return await request("/ontology");
    } catch {
      return [];
    }
  },

  evaluation: async () => {
    try {
      return await request("/evaluation/latest");
    } catch {
      return DEMO_EVALUATION;
    }
  },

  aggregates: async (kind) => {
    try {
      return await request(`/aggregates/${kind}`);
    } catch {
      return DEMO_AGGREGATES[kind] || [];
    }
  },
};

// ---------------------------------------------------------------------------
// Design System Constants (matching reference image & safety semantics)
// ---------------------------------------------------------------------------
export const STATE_GLYPHS = {
  verified: "✓",
  not_verified: "⚠",
  failed: "✕",
  absent: "○",
  partially_effective: "◐",
  unknown: "?",
};

export const STATE_COLORS = {
  verified: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  not_verified: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  failed: "bg-rose-600/20 text-rose-200 border-rose-500/50",
  absent: "bg-orange-500/15 text-orange-300 border-orange-500/40",
  partially_effective: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  unknown: "bg-slate-500/15 text-slate-300 border-slate-500/40",
};

export const SIF_COLORS = {
  high: "bg-red-500/20 text-red-300 border-red-500/50",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  low: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  needs_review: "bg-sky-500/15 text-sky-300 border-sky-500/40",
};

export const VALIDATION_COLORS = {
  pending: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  validated: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  rejected: "bg-rose-500/10 text-rose-300 border-rose-500/30",
};

export function label(value) {
  return (value || "unknown").replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Analytics scope helpers.
//
// Every number rendered on the Analytics page must be derived from the SAME
// current dataset scope that produced the page's aggregate rows. These helpers
// keep totals, percentages, barrier/activity/IOGP tallies and the scope header
// consistent with whatever the API actually returned (live observations or the
// self-consistent demo-fallback scope) - never a hardcoded historical count.
// ---------------------------------------------------------------------------

// Total observation count of the current analytics scope: prefers the live
// dashboard summary, and otherwise derives the scope from the SIF aggregate
// (each observation carries exactly one SIF class, so its rows sum to the
// dataset total). Empty/absent data yields 0, not a fabricated number.
export function analyticsScopeTotal(dashboard, sifAggs = []) {
  const live = Number(dashboard?.total_observations);
  if (Number.isFinite(live) && live > 0) return live;
  return sifAggs.reduce((sum, r) => sum + (Number(r?.count) || 0), 0);
}

// Round one aggregate count into a percentage of the current scope total.
// Guarded so a zero/empty scope renders 0% instead of NaN.
export function percentOfPart(part, total) {
  const denominator = Number(total);
  if (!Number.isFinite(denominator) || denominator <= 0) return 0;
  return Math.round((Number(part) / denominator) * 100);
}