// CAPA dashboard integration tests.
//
// These pin the pure summary helpers used to surface CAPA effectiveness on the
// main Barrier / Precursor dashboard (Overview card, Precursor Families strip,
// Precursor Family Detail section) against the existing 4 demo CAPA records, so
// the demo always demonstrates the integration and empty states stay empty.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEMO_CAPAS,
  pickCapaSignal,
  summarizeCapaForBarrier,
} from "../src/api.js";

const energyIsolation = summarizeCapaForBarrier(DEMO_CAPAS, "energy_isolation");
const hotWork = summarizeCapaForBarrier(DEMO_CAPAS, "hot_work_controls");
const machinery = summarizeCapaForBarrier(DEMO_CAPAS, "machinery_guarding");

test("energy_isolation barrier surfaces both demo CAPAs with correct tallies", () => {
  assert.equal(energyIsolation.total, 2);
  assert.equal(energyIsolation.open, 1); // CAPA-OBS-01
  assert.equal(energyIsolation.closed, 1); // CAPA-RECUR-01
  assert.equal(energyIsolation.recurrenceDetected, 1);
  assert.equal(energyIsolation.underObservation, 1);
  // Latest created wins the inline "View CAPA" (open under-observation is newer).
  assert.equal(energyIsolation.latest?.report_id, "CAPA-OBS-01");
});

test("hot_work_controls barrier shows the improvement CAPA", () => {
  assert.equal(hotWork.total, 1);
  assert.equal(hotWork.closed, 1);
  assert.equal(hotWork.improvementObserved, 1);
  assert.equal(hotWork.latest?.report_id, "CAPA-IMPR-01");
});

test("machinery_guarding barrier shows the insufficient-evidence CAPA", () => {
  assert.equal(machinery.total, 1);
  assert.equal(machinery.insufficientEvidence, 1);
  assert.equal(machinery.latest?.report_id, "CAPA-INSUF-01");
});

test("barrier without CAPAs yields an honest empty state (never fabricated)", () => {
  const none = summarizeCapaForBarrier(DEMO_CAPAS, "confined_space_procedure");
  assert.equal(none.total, 0);
  assert.equal(none.open, 0);
  assert.equal(none.closed, 0);
  assert.equal(none.recurrenceDetected, 0);
  assert.equal(none.improvementObserved, 0);
  assert.equal(none.underObservation, 0);
  assert.equal(none.insufficientEvidence, 0);
  assert.equal(none.latest, null);
  assert.deepEqual(none.capas, []);
});

test("signal selection prioritizes RECURRENCE DETECTED across the whole portfolio", () => {
  const signal = pickCapaSignal(DEMO_CAPAS);
  assert.equal(signal?.id, "CAPA-CAPA-RECUR-01");
  assert.equal(signal?.effectiveness_status, "recurrence_detected");
  assert.equal(signal?.post_capa?.recurrence_count, 1);
});

test("signal selection can be scoped to a family's barrier", () => {
  const scoped = pickCapaSignal(DEMO_CAPAS, ["hot_work_controls"]);
  assert.equal(scoped?.report_id, "CAPA-IMPR-01");
  assert.equal(scoped?.effectiveness_status, "improvement_observed");
});

test("signal selection returns null when no CAPAs are linked", () => {
  assert.equal(pickCapaSignal([]), null);
  assert.equal(pickCapaSignal(DEMO_CAPAS, ["fall_protection"]), null);
});

test("capas() maps camelCase browser filters to snake_case API params", async () => {
  const api = (await import("../src/api.js")).api;
  const calls = [];
  const originalFetch = global.fetch;
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      status: 200,
      json: async () => ({ total: 2, capas: [], limit: 100, offset: 0 }),
    };
  };
  try {
    await api.capas({ status: "closed", linkedBarrierId: "energy_isolation", limit: 100 });
  } finally {
    global.fetch = originalFetch;
  }
  assert.equal(calls.length, 1);
  const qs = calls[0].url.split("?")[1];
  assert.match(qs, /linked_barrier_id=energy_isolation/);
  assert.doesNotMatch(qs, /linkedBarrierId/);
  assert.match(qs, /status=closed/);
});
