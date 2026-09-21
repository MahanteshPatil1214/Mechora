// Analytics page scope consistency tests.
//
// These pin the pure helpers that drive the Analytics page: every displayed
// total / percentage / tally must be derived from the SAME current dataset
// scope that produced the aggregate rows — never from a hardcoded historical
// count (e.g. the old "248 Report" portfolio). They also pin the demo-fallback
// scope to be self-consistent so offline rendering never fabricates numbers.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  DEMO_DASHBOARD,
  DEMO_AGGREGATES,
  analyticsScopeTotal,
  percentOfPart,
} from "../src/api.js";

test("scope total prefers the live dashboard summary over aggregate sums", () => {
  const dashboard = { total_observations: 7 };
  const sif = [{ count: 4 }, { count: 3 }];
  assert.equal(analyticsScopeTotal(dashboard, sif), 7);
});

test("scope total falls back to the SIF aggregate sum when dashboard is absent", () => {
  const sif = [{ count: 4 }, { count: 3 }];
  assert.equal(analyticsScopeTotal(null, sif), 7);
  assert.equal(analyticsScopeTotal({}, sif), 7);
});

test("scope total is 0 (never a fabricated number) when no data exists", () => {
  assert.equal(analyticsScopeTotal(null, []), 0);
  assert.equal(analyticsScopeTotal({ total_observations: 0 }, []), 0);
  assert.equal(analyticsScopeTotal(undefined, undefined), 0);
});

test("percentOfPart rounds counts against the SAME scope total only", () => {
  const sif = [
    { classification: "high", count: 47 },
    { classification: "medium", count: 68 },
    { classification: "low", count: 112 },
    { classification: "needs_review", count: 21 },
  ];
  const total = analyticsScopeTotal(null, sif); // 248
  assert.equal(total, 248);
  const shares = sif.map((s) => percentOfPart(s.count, total));
  assert.deepEqual(shares, [19, 27, 45, 8]);
  assert.equal(shares.reduce((a, b) => a + b, 0), 99); // rounding keeps ~100
});

test("percentOfPart guards zero/absent scope (renders 0%, never NaN)", () => {
  assert.equal(percentOfPart(12, 0), 0);
  assert.equal(percentOfPart(12, null), 0);
  assert.equal(percentOfPart(12, undefined), 0);
  assert.equal(Number.isNaN(percentOfPart(12, 0)), false);
});

test("demo fallback scope is self-consistent: SIF rows sum to the dashboard total", () => {
  const sifTotal = DEMO_AGGREGATES.sif.reduce((s, r) => s + r.count, 0);
  assert.equal(sifTotal, DEMO_DASHBOARD.total_observations);
});

test("demo fallback scope totals/percentages add up from the same scope", () => {
  const total = analyticsScopeTotal(DEMO_DASHBOARD, DEMO_AGGREGATES.sif);
  assert.equal(total, DEMO_DASHBOARD.total_observations);
  // Every SIF class rendered as a share of the same scope total.
  const shares = DEMO_AGGREGATES.sif.map((s) => percentOfPart(s.count, total));
  assert.ok(shares.every((p) => p >= 0 && p <= 100));
});

test("Analytics page source contains no hardcoded legacy 248-report literal", async () => {
  const fs = await import("node:fs");
  const nodePath = await import("node:path");
  const { fileURLToPath } = await import("node:url");
  const testDir = nodePath.dirname(fileURLToPath(import.meta.url));
  const src = fs.readFileSync(
    nodePath.resolve(testDir, "../src/pages/Analytics.jsx"),
    "utf8",
  );
  assert.doesNotMatch(src, /248/);
});