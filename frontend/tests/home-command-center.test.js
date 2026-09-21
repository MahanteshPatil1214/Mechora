// Safety Intelligence Command Center helper tests.
//
// These pin the pure projections that drive the redesigned HSE Home page: CAPA
// portfolio counts, the per-barrier health table, high-signal event selection,
// top-family ranking and relative time. Every value is a projection of the same
// demo rows the workspace renders, so the dashboard can never fabricate a
// signal and empty data stays honest.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEMO_AGGREGATES,
  DEMO_CAPAS,
  DEMO_FAMILIES,
  buildEvidenceChain,
  deriveCapaPortfolio,
  deriveBarrierHealth,
  selectHighSignalObservations,
  selectTopFamilies,
  timeAgo,
} from "../src/api.js";

test("CAPA portfolio tallies the four verdicts from the demo rows", () => {
  const p = deriveCapaPortfolio(DEMO_CAPAS);
  assert.equal(p.total, 4);
  assert.equal(p.open, 1);
  assert.equal(p.closed, 3);
  assert.equal(p.underObservation, 1);
  assert.equal(p.improvementObserved, 1);
  assert.equal(p.recurrenceDetected, 1);
  assert.equal(p.insufficientEvidence, 1);
});

test("CAPA portfolio is all zeros for an empty dataset (never fabricated)", () => {
  const p = deriveCapaPortfolio([]);
  assert.deepEqual(p, {
    total: 0,
    open: 0,
    closed: 0,
    underObservation: 0,
    improvementObserved: 0,
    recurrenceDetected: 0,
    insufficientEvidence: 0,
  });
  assert.equal(deriveCapaPortfolio().total, 0);
});

test("barrier health derives status in fixed priority order", () => {
  const rows = deriveBarrierHealth(
    DEMO_AGGREGATES.barrier,
    DEMO_FAMILIES,
    DEMO_CAPAS,
  );
  assert.equal(rows.length, 5);

  const energy = rows.find((r) => r.barrier === "energy_isolation");
  assert.equal(energy.total, 50);
  assert.equal(energy.verified, 22);
  assert.equal(energy.failures, 28);
  assert.equal(energy.status, "Recurrence"); // CAPA recurrence wins over "Recurring"

  const hotWork = rows.find((r) => r.barrier === "hot_work_controls");
  assert.equal(hotWork.status, "Recurring");

  const fall = rows.find((r) => r.barrier === "fall_protection");
  assert.equal(fall.status, "Needs Review");

  // Highest failure count sorts first.
  assert.equal(rows[0].barrier, "energy_isolation");
});

test("barrier health ignores unknown barriers and handles empty input", () => {
  const rows = deriveBarrierHealth(
    [{ barrier: "unknown", barrier_state: "failed", count: 3 }],
    [],
    [],
  );
  assert.deepEqual(rows, []);
  assert.deepEqual(deriveBarrierHealth(), []);
});

test("high-signal selection keeps SIF-potential and failed-barrier events, newest first", () => {
  const obs = [
    {
      id: "OBS-1",
      created_at: "2026-01-01T00:00:00Z",
      event: { sif: { classification: "low" }, barrier_state: "verified" },
    },
    {
      id: "OBS-2",
      created_at: "2026-01-02T00:00:00Z",
      event: { sif: { classification: "high" }, barrier_state: "not_verified" },
    },
    {
      id: "OBS-3",
      created_at: "2026-01-03T00:00:00Z",
      event: { sif: { classification: "needs_review" }, barrier_state: "failed" },
    },
  ];
  const picked = selectHighSignalObservations(obs, 4);
  assert.deepEqual(
    picked.map((o) => o.id),
    ["OBS-3", "OBS-2"],
  );
  assert.deepEqual(selectHighSignalObservations([]), []);
  assert.deepEqual(selectHighSignalObservations(), []);
});

test("top families rank by attention signal, highest first", () => {
  const top = selectTopFamilies(DEMO_FAMILIES, 2);
  assert.deepEqual(
    top.map((f) => f.id),
    ["PFAM-001", "PFAM-002"],
  );
  assert.equal(top[0].attention_signal, 84.7);
});

test("timeAgo renders deterministic relative buckets", () => {
  const now = Date.UTC(2026, 0, 10, 12, 0, 0);
  const iso = (msAgo) => new Date(now - msAgo).toISOString();
  assert.equal(timeAgo(iso(30 * 1000), now), "just now");
  assert.equal(timeAgo(iso(4 * 60000), now), "4 min ago");
  assert.equal(timeAgo(iso(90 * 60000), now), "1 hr ago");
  assert.equal(timeAgo(iso(3 * 24 * 60 * 60000), now), "3 d ago");
  assert.equal(timeAgo("", now), "");
  assert.equal(timeAgo("not-a-date", now), "");
});

test("evidence chain projects the recurrence story from live family + CAPA rows", () => {
  const family = DEMO_FAMILIES.find((f) => f.id === "PFAM-001");
  const capa = DEMO_CAPAS.find((c) => c.effectiveness_status === "recurrence_detected");

  const chain = buildEvidenceChain(family, capa);

  assert.deepEqual(Object.keys(chain), ["failure", "capa", "evidence", "verdict"]);

  assert.equal(chain.failure.detail, "energy isolation · not verified");
  assert.deepEqual(chain.failure.facts, ["4 reports", "4 sites"]);
  assert.equal(chain.failure.to, "/app/families/PFAM-001");

  assert.equal(chain.capa.detail, "CAPA-RECUR-01 · Closed");
  assert.deepEqual(chain.capa.facts, ["3 baseline failures"]);
  assert.equal(chain.capa.to, `/app/capas/${capa.id}`);

  assert.equal(chain.evidence.detail, "Recurrence observed");
  assert.deepEqual(chain.evidence.facts, ["1 recurrence", "1 post-closure obs"]);

  assert.equal(chain.verdict.status, "recurrence_detected");
  assert.equal(chain.verdict.tone, "rose");
  assert.ok(chain.verdict.facts.length > 0);
});

test("evidence chain handles an absent CAPA honestly", () => {
  const family = DEMO_FAMILIES.find((f) => f.id === "PFAM-002");
  const chain = buildEvidenceChain(family, null);

  assert.equal(chain.capa.detail, "No CAPA linked yet");
  assert.equal(chain.capa.to, null);
  assert.deepEqual(chain.capa.facts, ["Create a CAPA to begin tracking"]);

  assert.equal(chain.evidence.detail, "Waiting for a linked CAPA");
  assert.deepEqual(chain.evidence.facts, []);

  assert.equal(chain.verdict.status, null);
  assert.equal(chain.verdict.detail, "Not yet assessed");
  assert.equal(chain.verdict.tone, "slate");
});

test("evidence chain tolerates an absent family too", () => {
  const chain = buildEvidenceChain(null, null);
  assert.equal(chain.failure.detail, "No precursor family");
  assert.equal(chain.failure.to, null);
});
