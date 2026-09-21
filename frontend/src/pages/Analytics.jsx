import React, { useState, useEffect } from "react";
import {
  BarChart3,
  ShieldCheck,
  Cpu,
  Clock,
} from "lucide-react";
import { api, label, analyticsScopeTotal, percentOfPart } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge } from "../components/common/StatusBadge.jsx";

function SectionEmpty({ message = "No data available" }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 bg-slate-950/50 py-10 text-center space-y-1.5">
      <BarChart3 size={20} className="text-slate-600" />
      <p className="text-xs font-bold text-slate-400">{message}</p>
      <p className="text-[10px] text-slate-600">
        Nothing to display for the current dataset scope.
      </p>
    </div>
  );
}

function SectionLoading() {
  return (
    <div className="flex items-center justify-center rounded-lg border border-slate-800 bg-slate-950/50 py-10 animate-pulse">
      <p className="text-xs font-bold text-slate-500">Loading…</p>
    </div>
  );
}

// Worst-case pass rate (%) across the critical assertion suite, derived from the
// evaluation record's own per-assertion accuracies - never a hardcoded figure.
function suitePassRate(suite) {
  const accs = Object.values(suite || {}).map((row) => Number(row?.accuracy));
  const valid = accs.filter((a) => Number.isFinite(a));
  if (valid.length === 0) return null;
  return Math.round(Math.min(...valid) * 100);
}

export default function Analytics() {
  const [activeTab, setActiveTab] = useState("operational"); // operational | evaluation
  const [evalData, setEvalData] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [barrierAggs, setBarrierAggs] = useState([]);
  const [activityAggs, setActivityAggs] = useState([]);
  const [sifAggs, setSifAggs] = useState([]);
  const [lsrAggs, setLsrAggs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.evaluation().catch(() => null),
      api.dashboard().catch(() => null),
      api.aggregates("barrier").catch(() => []),
      api.aggregates("activity").catch(() => []),
      api.aggregates("sif").catch(() => []),
      api.aggregates("lsr").catch(() => []),
    ]).then(([evaluation, dash, barriers, activities, sifs, lsrs]) => {
      setEvalData(evaluation);
      setDashboard(dash);
      setBarrierAggs(barriers || []);
      setActivityAggs(activities || []);
      setSifAggs(sifs || []);
      setLsrAggs(lsrs || []);
      setLoading(false);
    });
  }, []);

  // Single source of truth for every total/percentage on the page: the scope
  // total is derived from the same API data that produced the aggregate rows.
  const scopeTotal = analyticsScopeTotal(dashboard, sifAggs);
  const scopeLabel = loading
    ? "…"
    : scopeTotal > 0
      ? `${scopeTotal} Records`
      : "No data available";
  const evalCount = evalData?.metrics?.record_count ?? null;
  const evalLabel = loading ? "…" : evalCount != null ? String(evalCount) : "—";
  const passRate = suitePassRate(evalData?.metrics?.critical_suite);

  return (
    <div className="space-y-6">
      {/* Enterprise Page Header */}
      <PageHeader
        title="HSE Safety Intelligence & Analytics"
        subtitle="Systemic recurrence patterns, critical barrier failure frequencies, and model evaluation benchmarks."
        breadcrumbs={[{ label: "Analytics & Benchmarks" }]}
        actions={
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
            <Clock size={14} />
            <span>Dataset: Current Analytics Scope ({scopeLabel})</span>
          </div>
        }
      />

      {/* Main Tabs */}
      <div className="flex border-b border-slate-800 gap-6 text-xs font-bold">
        <button
          type="button"
          onClick={() => setActiveTab("operational")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "operational"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BarChart3 size={15} />
          <span>Operational Safety Trends</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("evaluation")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "evaluation"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu size={15} />
          <span>Model Evaluation Benchmark (n={evalLabel})</span>
        </button>
      </div>

      {/* TAB 1: OPERATIONAL SAFETY TRENDS */}
      {activeTab === "operational" && (
        <div className="space-y-6">
          {/* Top Row: Barrier Failure Frequencies & Activity Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Barrier Failures */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Barrier Breakdown Frequency by State
                  </h3>
                  <p className="text-[10px] text-slate-400">Aggregated from stored observation records</p>
                </div>
                <span className="rounded border border-rose-500/30 bg-rose-500/10 px-2.5 py-0.5 text-[10px] font-bold text-rose-300">
                  Critical Focus
                </span>
              </div>

              {loading ? (
                <SectionLoading />
              ) : barrierAggs.length === 0 ? (
                <SectionEmpty message="No barrier breakdown data available" />
              ) : (
                <div className="space-y-2.5">
                  {barrierAggs.map((b, idx) => {
                    const maxCount = barrierAggs[0]?.count || 1;
                    const pct = Math.round((b.count / maxCount) * 100);
                    const isFailure =
                      b.barrier_state === "not_verified" ||
                      b.barrier_state === "failed" ||
                      b.barrier_state === "absent";

                    return (
                      <div
                        key={idx}
                        className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-200 capitalize">
                            {label(b.barrier)}
                          </span>
                          <div className="flex items-center gap-2">
                            <StateBadge value={b.barrier_state} />
                            <span className="font-mono font-bold text-white">{b.count}</span>
                          </div>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                          <div
                            className={`h-full rounded-full transition-all ${
                              isFailure ? "bg-rose-500" : "bg-emerald-500"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Activity Distribution */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Observations by Activity / Equipment
                  </h3>
                  <p className="text-[10px] text-slate-400">Cross-operational representation</p>
                </div>
                <span className="text-[10px] font-mono text-slate-500">{scopeLabel} in Scope</span>
              </div>

              {loading ? (
                <SectionLoading />
              ) : activityAggs.length === 0 ? (
                <SectionEmpty message="No activity data available" />
              ) : (
                <div className="space-y-2.5">
                  {activityAggs.map((a, idx) => {
                    const maxCount = activityAggs[0]?.count || 1;
                    const pct = Math.round((a.count / maxCount) * 100);

                    return (
                      <div
                        key={idx}
                        className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-200 capitalize">
                            {label(a.activity)}
                          </span>
                          <span className="font-mono font-bold text-slate-300">{a.count} reports</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                          <div
                            className="h-full rounded-full bg-amber-500 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Bottom Row: SIF Potential Breakdown & LSR Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* SIF Potential Distribution */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                  SIF-Potential Distribution
                </h3>
                <span className="text-[10px] text-slate-400 font-mono">Decision-Support Prioritization</span>
              </div>

              {loading ? (
                <SectionLoading />
              ) : sifAggs.length === 0 ? (
                <SectionEmpty message="No SIF classification data available" />
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {sifAggs.map((s, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-1.5"
                    >
                      <SIFBadge value={s.classification} />
                      <div className="text-2xl font-black text-white font-mono">{s.count}</div>
                      <div className="text-[11px] text-slate-400">
                        {percentOfPart(s.count, scopeTotal)}% of total observations
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Life-Saving Rules Correlated */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                  IOGP Life-Saving Rules Correlation
                </h3>
                <span className="text-[10px] text-slate-400">High-hazard controls</span>
              </div>

              {loading ? (
                <SectionLoading />
              ) : lsrAggs.length === 0 ? (
                <SectionEmpty message="No IOGP life-saving rule data available" />
              ) : (
                <div className="space-y-2">
                  {lsrAggs.map((l, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs"
                    >
                      <span className="font-semibold text-slate-200 capitalize">
                        {label(l.life_saving_rule)}
                      </span>
                      <span className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 font-mono text-xs font-bold text-amber-300">
                        {l.count}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: MODEL EVALUATION BENCHMARK */}
      {activeTab === "evaluation" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 text-xs text-sky-200 flex items-start gap-3">
            <ShieldCheck size={18} className="text-sky-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-bold text-white block">
                Deterministic Model Evaluation Benchmark ({evalData?.run_id || "Not yet run"})
              </span>
              <span className="text-slate-300">
                Scored against the curated {evalLabel}-record evaluation suite. All numbers here are produced
                by deterministic offline rule assertions — zero fabricated metrics or simulated numbers.
              </span>
            </div>
          </div>

          {!loading && !evalData ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
              <SectionEmpty message="No stored evaluation metrics available" />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Field Accuracy */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Per-Field Extraction Accuracy (Exact Ground Truth Match)
                  </h3>
                  <span className="font-mono text-xs font-bold text-amber-400">
                    n={evalLabel}
                  </span>
                </div>

                {Object.keys(evalData?.metrics?.field_accuracy || {}).length === 0 ? (
                  <SectionEmpty message="No field accuracy metrics available" />
                ) : (
                  <div className="space-y-2">
                    {Object.entries(evalData?.metrics?.field_accuracy || {}).map(([field, score]) => (
                      <div
                        key={field}
                        className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs"
                      >
                        <span className="font-medium text-slate-300 capitalize">{label(field)}</span>
                        <span className="font-mono font-bold text-emerald-400">
                          {(score * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Critical Assertions & SIF Macro-F1 */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                    Critical Assertion Suite & SIF Metric
                  </h3>
                  <span className="text-[10px] font-bold text-emerald-400">
                    {passRate != null ? `${passRate}% Passed` : "No data"}
                  </span>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white text-xs">SIF Classification Macro-F1</div>
                    <div className="text-[10px] text-slate-500">Multi-class balanced harmonic mean</div>
                  </div>
                  <div className="font-mono text-lg font-black text-amber-400">
                    {typeof evalData?.metrics?.sif?.macro_f1 === "number"
                      ? evalData.metrics.sif.macro_f1.toFixed(3)
                      : "—"}
                  </div>
                </div>

                {Object.keys(evalData?.metrics?.critical_suite || {}).length === 0 ? (
                  <SectionEmpty message="No critical assertion suite data available" />
                ) : (
                  <div className="space-y-2">
                    {Object.entries(evalData?.metrics?.critical_suite || {}).map(([name, res]) => (
                      <div
                        key={name}
                        className="rounded-lg border border-slate-800 bg-slate-950 p-3 flex items-center justify-between text-xs"
                      >
                        <div>
                          <div className="font-semibold text-slate-200 capitalize">
                            {label(name.split(" ")[0])}
                          </div>
                          <div className="text-[10px] text-slate-500">{name}</div>
                        </div>
                        <span className="rounded bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 font-mono font-bold text-emerald-300 text-xs">
                          {(Number(res?.accuracy || 0) * 100).toFixed(1)}% Pass
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <p className="text-[10px] italic text-slate-500 pt-2 border-t border-slate-800">
                  Generated via scripts/run_evaluation.py against data/evaluation/eval_set.json.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mandatory Disclaimer */}
      <div className="text-center pt-4">
        <p className="text-xs italic text-slate-500">
          Prototype HSE Attention Signal — decision support, not an official OIL risk score or accident prediction.
        </p>
      </div>
    </div>
  );
}