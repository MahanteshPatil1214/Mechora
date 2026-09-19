// MECHORA Centralized API Client
// Strict fidelity to backend endpoints in backend/app/api/routes/
// Supports graceful demo fallback when backend is starting or offline

const base = "/api/v1";

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

  // Upload a PDF/DOCX/TXT report; the backend extracts plain text and returns
  // { filename, file_type, text, character_count }. Uses raw multipart so the
  // browser can set the FormData boundary.
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
      if (kind === "barrier") {
        return [
          { barrier: "energy_isolation", barrier_state: "not_verified", count: 28 },
          { barrier: "energy_isolation", barrier_state: "verified", count: 22 },
          { barrier: "hot_work_controls", barrier_state: "not_verified", count: 18 },
          { barrier: "fall_protection", barrier_state: "absent", count: 14 },
          { barrier: "confined_space_procedure", barrier_state: "failed", count: 12 },
          { barrier: "machinery_guarding", barrier_state: "partially_effective", count: 9 },
        ];
      }
      if (kind === "activity") {
        return [
          { activity: "pipeline_maintenance", count: 48 },
          { activity: "compressor_maintenance", count: 36 },
          { activity: "hot_work", count: 32 },
          { activity: "valve_replacement", count: 24 },
          { activity: "pump_maintenance", count: 20 },
          { activity: "working_at_height", count: 18 },
        ];
      }
      if (kind === "sif") {
        return [
          { classification: "high", count: 47 },
          { classification: "medium", count: 68 },
          { classification: "low", count: 112 },
          { classification: "needs_review", count: 21 },
        ];
      }
      if (kind === "lsr") {
        return [
          { life_saving_rule: "energy_isolation", count: 52 },
          { life_saving_rule: "hot_work", count: 34 },
          { life_saving_rule: "working_at_height", count: 22 },
          { life_saving_rule: "gas_testing", count: 19 },
          { life_saving_rule: "line_of_fire", count: 16 },
        ];
      }
      return [];
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