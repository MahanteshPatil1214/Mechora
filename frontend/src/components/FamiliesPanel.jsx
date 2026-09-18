import { useEffect, useState } from "react";
import { api, label } from "../api.js";
import { SIFBadge, StateBadge, FamilyTypeBadge } from "./Badge.jsx";

const GE_GLYPH = { same: "✓", mixed: "△", distinct: "×" };

function AttentionBar({ value, basis = [], factors = {}, familyType = "precursor" }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));

  let levelLabel = "Routine Observation";
  let levelColor = "border-sky-500/40 bg-sky-500/10 text-sky-300";
  let barColor = "bg-sky-500";

  if (familyType === "controlled") {
    levelLabel = "Controlled / Verified Check";
    levelColor = "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
    barColor = "bg-emerald-500";
  } else if (familyType === "needs_review") {
    levelLabel = "Incomplete / Needs HSE Review";
    levelColor = "border-amber-500/40 bg-amber-500/10 text-amber-300";
    barColor = "bg-amber-500";
  } else if (v >= 70) {
    levelLabel = "Elevated Precursor Attention";
    levelColor = "border-rose-500/40 bg-rose-500/15 text-rose-300";
    barColor = "bg-rose-500";
  } else if (v >= 40) {
    levelLabel = "Guarded Precursor Attention";
    levelColor = "border-amber-500/40 bg-amber-500/15 text-amber-300";
    barColor = "bg-amber-500";
  }

  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/70 p-2.5 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
            HSE Attention Signal
          </span>
          <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-500 lowercase">
            prototype
          </span>
        </div>
        <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${levelColor}`}>
          {levelLabel}
        </span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${barColor} transition-all duration-300`} style={{ width: `${Math.round(v)}%` }} />
      </div>

      <div className="text-[10px] text-slate-400 font-mono">
        Prototype Attention Index: <strong className="text-slate-200">{Math.round(v)}/100</strong>
        <span className="text-slate-500 italic font-sans"> — engineering heuristic, not a probability or risk percentage</span>
      </div>

      {basis && basis.length > 0 && (
        <div className="space-y-1 pt-0.5">
          <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold">
            Contributing Factors:
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 pt-0.5">
            {basis.map((b, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                <span className="text-sky-400 font-bold">•</span>
                <span>{b}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-[9px] italic text-slate-500">
        Prototype HSE Attention Signal — decision-support heuristic for human HSE triage. Not an official OIL risk score and not accident prediction.
      </p>
    </div>
  );
}

function GroupingChips({ evidence, coreMechanism, context }) {
  const [expanded, setExpanded] = useState(false);
  if (!evidence?.length) return null;

  const unknownDims = evidence.filter((g) => g.status === "unknown");
  const known = evidence.filter((g) => g.status !== "unknown");
  const matchingDimensions = known.filter((g) => g.status === "same");
  const differingDimensions = known.filter((g) => g.status !== "same");

  return (
    <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2.5 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            Why Grouped:
          </span>

          {/* Matching Mechanism Chips */}
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-[9px] font-mono text-emerald-400/80 mr-0.5">Matching:</span>
            {matchingDimensions.map((g) => (
              <span
                key={g.dimension}
                title={`${label(g.dimension)}: ${label(g.value)} (${g.note || "Matching across all observations"})`}
                className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium border border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
              >
                <span className="font-bold">✓</span>
                <span>{label(g.dimension)}</span>
              </span>
            ))}
          </div>

          {/* Differing Context Chips */}
          {differingDimensions.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 ml-1 pl-1 border-l border-emerald-500/30">
              <span className="text-[9px] font-mono text-amber-400/80 mr-0.5">Differing (Allowed):</span>
              {differingDimensions.map((g) => (
                <span
                  key={g.dimension}
                  title={`${label(g.dimension)}: ${label(g.value)} dominant (${g.note})`}
                  className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium border border-amber-500/30 bg-amber-500/10 text-amber-200"
                >
                  <span className="font-bold">△</span>
                  <span>{label(g.dimension)}</span>
                </span>
              ))}
            </div>
          )}

          {context?.distinct_activities_count > 1 && (
            <span className="rounded border border-purple-500/30 bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-purple-300">
              Across {context.distinct_activities_count} Diverse Activities
            </span>
          )}
          {unknownDims.length > 0 && (
            <span className="rounded border border-slate-700 bg-slate-800/50 px-1.5 py-0.5 text-[9px] text-slate-400 italic">
              N/A (unknown across members): {unknownDims.map((g) => label(g.dimension)).join(", ")}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-[10px] font-mono text-emerald-400/90 hover:text-emerald-300 transition-colors cursor-pointer"
        >
          {expanded ? "Hide Reasoning ▲" : "Inspect Mechanism Reasoning ▼"}
        </button>
      </div>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-emerald-500/20 space-y-2">
          {/* Matching dimensions */}
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1">
              <span>✓</span> Matching Mechanism Dimensions (Invariant)
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {matchingDimensions.map((g) => (
                <div
                  key={g.dimension}
                  className="flex items-center justify-between rounded bg-slate-900/90 px-2 py-1.5 text-[11px] border border-emerald-500/30"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-emerald-400">✓</span>
                    <span className="capitalize text-slate-400">{label(g.dimension)}:</span>
                    <span className="font-semibold text-emerald-200">{label(g.value) || "Unknown"}</span>
                  </div>
                  <span className="text-[10px] text-emerald-400/80 font-mono">100% agreement</span>
                </div>
              ))}
            </div>
          </div>

          {/* Differing dimensions and reason why allowed */}
          {differingDimensions.length > 0 && (
            <div className="space-y-1 pt-1">
              <div className="text-[10px] uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1">
                <span>△</span> Differing Dimensions &amp; Why Allowed
              </div>
              <div className="space-y-1">
                {differingDimensions.map((g) => (
                  <div
                    key={g.dimension}
                    className="rounded bg-slate-900/90 p-2 text-[11px] border border-slate-800 space-y-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-amber-400">△</span>
                        <span className="capitalize text-slate-400">{label(g.dimension)}:</span>
                        <span className="font-semibold text-slate-200">{label(g.value)} dominant</span>
                      </div>
                      <span className="text-[10px] text-amber-300/80 font-mono">operational context</span>
                    </div>
                    <p className="text-[10px] text-slate-400 italic leading-relaxed">
                      {g.note || `Differing ${label(g.dimension)} is permitted because the core barrier failure and energy hazard are identical across member events.`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded bg-slate-900/60 p-2 text-[11px] text-emerald-300/80 border border-emerald-500/10 space-y-1">
            <div className="font-semibold text-emerald-300">Structural Clustering Principle:</div>
            <p className="leading-relaxed">
              Events are clustered by invariant physical barrier mechanism rather than narrative keyword overlap. Different equipment, locations, and activity phrases (e.g. Pump vs Pipeline vs Compressor) do NOT split the family when the underlying barrier and energy mechanism are identical.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function ExclusionList({ exclusions }) {
  if (!exclusions?.length) return null;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-slate-400 font-semibold">
        Why NOT Grouped (Mechanism Separation)
      </div>
      <div className="space-y-2">
        {exclusions.map((e, i) => {
          const differs = e.dimension_comparisons?.filter((c) => c.match === "differs") || [];
          const shared = e.dimension_comparisons?.filter((c) => c.match === "same") || [];
          return (
            <div
              key={`${e.other_family_id}-${i}`}
              className="rounded-md border border-slate-800 bg-slate-900/90 p-2.5 text-[11px] space-y-2"
            >
              <div className="flex flex-wrap items-center justify-between gap-1">
                <div className="font-medium text-slate-200">
                  Separated from <span className="font-mono text-sky-300 font-semibold">{e.other_family_id}</span>
                  {e.other_family_name && (
                    <span className="ml-1 text-slate-300 font-normal">({e.other_family_name})</span>
                  )}
                </div>
                <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                  Distinct Safety Mechanism
                </span>
              </div>

              {/* Separation cause banner */}
              {e.basis && (
                <div className="rounded border border-rose-500/40 bg-rose-500/10 px-2.5 py-1.5 text-[11px] font-medium text-rose-200 space-y-0.5">
                  <div className="text-[9px] uppercase tracking-wider text-rose-400/90 font-bold">
                    Primary Separation Cause:
                  </div>
                  <div>{e.basis}</div>
                </div>
              )}

              {/* Differing and Shared dimensions breakdown */}
              {differs.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-rose-400 font-semibold">
                    Differing Critical Dimensions:
                  </span>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {differs.map((dc) => (
                      <span
                        key={dc.dimension}
                        className="inline-flex items-center gap-1 rounded border border-rose-500/40 bg-rose-500/15 px-2 py-0.5 text-[10px] text-rose-200"
                      >
                        <span className="capitalize text-rose-300 font-medium">{label(dc.dimension)}:</span>
                        <span className="font-semibold text-white">{dc.this_label || label(dc.this_value)}</span>
                        <span className="text-rose-400 font-bold mx-0.5">≠</span>
                        <span className="text-slate-300">{dc.other_label || label(dc.other_value)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {shared.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                    Shared Contextual Dimensions:
                  </span>
                  <div className="mt-0.5 flex flex-wrap gap-1">
                    {shared.map((dc) => (
                      <span
                        key={dc.dimension}
                        className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-300"
                      >
                        <span className="capitalize text-slate-400">{label(dc.dimension)}:</span>
                        <span>{dc.this_label || label(dc.this_value)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function FamiliesPanel() {
  const [rows, setRows] = useState([]);
  const [recOnly, setRecOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState("all");
  const [err, setErr] = useState("");

  useEffect(() => {
    api.families(recOnly)
      .then((res) => setRows(res.families || []))
      .catch((e) => setErr(e.message));
  }, [recOnly]);

  const filteredRows = rows.filter((f) => {
    if (typeFilter === "all") return true;
    return (f.family_type || "precursor") === typeFilter;
  });

  const precursorCount = rows.filter((f) => (f.family_type || "precursor") === "precursor").length;
  const controlledCount = rows.filter((f) => f.family_type === "controlled").length;
  const reviewCount = rows.filter((f) => f.family_type === "needs_review").length;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-4">
      {/* Header and Filter Controls */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-300">
              Structural Safety Families
            </h2>
            <p className="text-xs text-slate-500">
              Clustering recurring failure mechanisms across varied narratives, tasks, and equipment.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
            <input
              type="checkbox"
              checked={recOnly}
              onChange={(e) => setRecOnly(e.target.checked)}
              className="accent-sky-500 cursor-pointer"
            />
            <span>Recurring only (≥ 2 reports)</span>
          </label>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          <button
            type="button"
            onClick={() => setTypeFilter("all")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              typeFilter === "all"
                ? "border-sky-500 bg-sky-500/20 text-sky-200"
                : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            All Families ({rows.length})
          </button>
          <button
            type="button"
            onClick={() => setTypeFilter("precursor")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              typeFilter === "precursor"
                ? "border-rose-500 bg-rose-500/20 text-rose-200"
                : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            Precursors ({precursorCount})
          </button>
          <button
            type="button"
            onClick={() => setTypeFilter("controlled")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              typeFilter === "controlled"
                ? "border-emerald-500 bg-emerald-500/20 text-emerald-200"
                : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            Controlled ({controlledCount})
          </button>
          <button
            type="button"
            onClick={() => setTypeFilter("needs_review")}
            className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              typeFilter === "needs_review"
                ? "border-amber-500 bg-amber-500/20 text-amber-200"
                : "border-slate-800 bg-slate-950 text-slate-400 hover:text-slate-200"
            }`}
          >
            Needs Review ({reviewCount})
          </button>
        </div>
      </div>

      {err && (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {err}
        </p>
      )}

      {/* Family Cards */}
      <div className="space-y-3.5">
        {filteredRows.map((f) => {
          const core = f.core_mechanism || {};
          const ctx = f.context || {};
          const rec = f.recurrence || {};
          const activitiesList = ctx.activities || [];

          return (
            <div
              key={f.id}
              className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-3 shadow-sm hover:border-slate-700 transition-colors"
            >
              {/* Header */}
              <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <FamilyTypeBadge type={f.family_type} />
                    <span className="text-sm font-bold text-slate-100">{f.name}</span>
                    {f.recurring && (
                      <span className="rounded-md border border-rose-500/50 bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-rose-300">
                        recurring ({f.observation_ids.length} obs / {rec.distinct_activities_count || activitiesList.length} activities)
                      </span>
                    )}
                    {!f.recurring && f.family_type !== "controlled" && (
                      <span className="rounded-md border border-slate-600/60 bg-slate-800/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-400">
                        single — recurrence not established
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{f.description}</p>
                </div>
                <span className="text-xs text-slate-400 font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  {f.id}
                </span>
              </div>

              {/* Why it matters callout */}
              {f.why_it_matters && (
                <div className="rounded-md border border-sky-500/30 bg-sky-500/10 p-2.5 text-xs text-sky-200">
                  <span className="font-semibold text-sky-300">Safety Significance: </span>
                  <span>{f.why_it_matters}</span>
                </div>
              )}

              {/* Core Mechanism vs Context Variation Split */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
                {/* Core Invariant Mechanism */}
                <div className="rounded-md border border-slate-800 bg-slate-900/60 p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800 pb-1">
                    <span>Core Safety Mechanism (Invariant)</span>
                    <span className="text-emerald-400 font-normal lowercase">mechanism match</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-0.5">
                    <div>
                      <span className="text-[10px] text-slate-400">Energy / Hazard:</span>
                      <div className="font-medium text-slate-200 capitalize">
                        {label(core.energy || f.common_energy)}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Barrier:</span>
                      <div className="font-medium text-slate-200 capitalize">
                        {label(core.barrier || f.common_barrier)}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Barrier State:</span>
                      <div className="pt-0.5">
                        <StateBadge value={core.barrier_state || f.common_barrier_state} />
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Exposure:</span>
                      <div className="font-medium text-slate-200 capitalize">
                        {core.exposure && core.exposure !== "unknown"
                          ? label(core.exposure)
                          : (f.common_exposure && f.common_exposure !== "unknown"
                              ? label(f.common_exposure)
                              : "Unknown / Varies")}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Context Variations */}
                <div className="rounded-md border border-slate-800 bg-slate-900/60 p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800 pb-1">
                    <span>Context Variations (Allowed Divergence)</span>
                    <span className="text-sky-400 font-normal lowercase">diverse tasks</span>
                  </div>
                  <div className="space-y-1.5 pt-0.5">
                    <div>
                      <span className="text-[10px] text-slate-400">Task Phase: </span>
                      <span className="font-medium text-slate-200 capitalize">
                        {label(ctx.task_phase || f.signature?.task_phase || "Maintenance")}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block mb-1">
                        Activities Covered ({activitiesList.length || 1}):
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {activitiesList.length > 0 ? (
                          activitiesList.map((act) => (
                            <span
                              key={act}
                              className="rounded border border-slate-700 bg-slate-800/80 px-1.5 py-0.5 text-[10px] text-slate-300 capitalize font-medium"
                            >
                              {label(act)}
                            </span>
                          ))
                        ) : (
                          <span className="text-[10px] text-slate-400 italic">None specified</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* SIF Potential Summary Line */}
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 pt-0.5">
                <span>SIF Potential:</span>
                <SIFBadge value={f.sif_potential_count > 0 ? "high" : "needs_review"} />
                <span>({f.sif_potential_count} of {f.observation_ids.length} observations)</span>
                <span className="ml-auto text-slate-500 font-mono text-[11px]">
                  {f.observation_ids.length} linked reports
                </span>
              </div>

              {/* HSE Attention Signal */}
              <AttentionBar
                value={f.attention_signal}
                basis={f.attention_basis}
                factors={f.attention_factors}
                familyType={f.family_type}
              />

              {/* Dynamic Why Grouped & Why Not Grouped */}
              <div className="space-y-2 pt-1 border-t border-slate-800/80">
                <GroupingChips
                  evidence={f.grouping_evidence}
                  coreMechanism={core}
                  context={ctx}
                />
                <ExclusionList exclusions={f.exclusions} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}