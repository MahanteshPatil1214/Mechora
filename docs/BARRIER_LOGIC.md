# MECHORA Safety Logic & Barrier Mechanism Principles

This document defines the formal safety engineering principles implemented in MECHORA's deterministic safety intelligence engine.

---

## 1. Procedural Verification Omission (`not_verified`) vs. Physical Hardware Failure (`failed`)

In industrial HSE and Process Safety Management (CCPS / IOGP / OSHA 1910.119), a barrier failure can occur along two fundamentally different failure vectors:

### A. Procedural Verification Omission (`not_verified`)
- **Nature:** Human, procedural, or operational barrier verification was skipped, omitted, or incomplete prior to commencing work on energized systems.
- **Examples:**
  - *"Technician opened the crude flange without verifying zero energy."*
  - *"Lockout was not confirmed prior to casing removal."*
  - *"Zero pressure had not been proven before line break."*
- **Root Causes:** Procedural drift, permit-to-work (PTW) non-compliance, time pressure, lack of isolation confirmation checklists.
- **Targeted HSE Interventions:**
  - Mandatory "Verify Zero Energy" check-stops in PTW workflows.
  - Independent lock-out / tag-out (LOTO) field audits.
  - Pre-job safety toolbox talks focused on positive isolation verification.

### B. Physical Hardware / Mechanical Integrity Breakdown (`failed`)
- **Nature:** Physical hardware, valve seat, blind flange, or mechanical containment ruptured, leaked through, blew out, or degraded under operational pressure.
- **Examples:**
  - *"High-pressure isolation valve ruptured and failed to hold pressure."*
  - *"Flange gasket blew out under hydrotest pressure."*
  - *"Double-block-and-bleed valve passing fluid past the seat."*
- **Root Causes:** Mechanical fatigue, erosion/corrosion, overpressure, valve packing degradation, manufacturing defect.
- **Targeted HSE Interventions:**
  - Mechanical integrity inspection and valve overhaul schedules.
  - Acoustic leak detection and ultrasonic seat testing.
  - Material specification review and pressure relief calibration.

### Precursor Engine Clustering Decision
Because the required corrective actions are completely different (procedural auditing vs. mechanical asset replacement), **MECHORA strictly separates `not_verified` and `failed` into distinct Precursor Families**. Grouping them would obscure whether an asset has a procedural compliance problem or a physical hardware integrity degradation problem.

The `WHY NOT GROUPED` module explicitly surfaces this distinction:
```
Barrier State: Not Verified ≠ Failed → DIFFERENT MECHANISM (Procedural Verification Omission vs. Physical Hardware Failure)
```

---

## 2. Potential Consequence: Non-Invention Principle

### Principle:
- **Verified Barrier Checks:** When an observation records that a barrier was successfully verified, proven depressurized, or tested with zero energy (`barrier_state == "verified"`), **MECHORA never assigns `serious_injury_or_fatality` potential**.
- A verified barrier check confirms that risk controls were effective. Inferring severe consequence solely because hazardous energy was present on the site is an error that distorts safety reporting.
- **Unknown / Needs Review:** If the narrative does not provide explicit evidence of a near-miss, loss of containment, or hazardous breach, the potential consequence is recorded as `unknown` and flagged in the UI as `Unknown / Needs Review`.
- Only when an unmitigated barrier failure occurs in the presence of high-hazard energy or hazardous exposure (or explicit near-miss narrative evidence) is severe potential assigned.

---

## 3. Exposure Aggregation: Strict Consensus Principle

### Principle:
- **No Family-Level Invention:** When aggregating individual safety observations into a Structural Precursor Family, the system **never infers a common exposure** if the member reports do not support it.
- **Consensus Rule:** A family is only assigned a `common_exposure` if a solid majority ($\ge 50\%$) of member observations explicitly share that known exposure.
- If individual observations record `Unknown` or have divergent exposures, the family summary explicitly states:
  `Exposure: Unknown / unconfirmed across member reports`
  rather than elevating a single observation's exposure to the entire family.

---

## 4. Grounded Verbatim Evidence vs. Canonical Concepts

### Principle:
- **Canonical Concept:** Standardized ontology key representing the physical barrier or energy (e.g., `Energy Isolation`, `Pressurized Gas`, `Line Break Maintenance`).
- **Verbatim Evidence:** Exact text span extracted directly from the narrative (e.g., `"zero energy was never checked"`, `"lockout"`, `"hydrocarbon release"`).
- In both API responses and UI components, canonical labels and verbatim evidence spans are strictly segregated and clearly labelled so human HSE reviewers never confuse an ontology concept with the source text.
