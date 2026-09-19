import React from "react";
import { label } from "../../api.js";

export function GroupingBreakdown({
  evidence = [],
  title = "WHY THESE REPORTS FORM ONE PRECURSOR PATTERN",
  subtitle = "Per-dimension comparison over family members",
}) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-800 pb-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
          {title}
        </h3>
        <span className="text-xs text-slate-400">
          {subtitle}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 uppercase text-[11px]">
              <th className="pb-2.5 font-semibold">Dimension</th>
              <th className="pb-2.5 font-semibold">Dominant Canonical Value</th>
              <th className="pb-2.5 font-semibold">Status</th>
              <th className="pb-2.5 font-semibold">Coverage</th>
              <th className="pb-2.5 font-semibold">Engineering Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200">
            {evidence.map((g) => {
              const coveragePct = Math.round((g.coverage ?? 0) * 100);
              const isMatch = g.status === "same";
              const isMixed = g.status === "mixed";

              return (
                <tr key={g.dimension} className="hover:bg-slate-800/30">
                  <td className="py-2.5 font-semibold uppercase text-slate-300">
                    {label(g.dimension)}
                  </td>
                  <td className="py-2.5 font-medium capitalize text-white">
                    {label(g.value) || "Unknown"}
                  </td>
                  <td className="py-2.5">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-[11px] font-bold border ${
                        isMatch
                          ? "bg-emerald-950/60 text-emerald-300 border-emerald-700/60"
                          : isMixed
                          ? "bg-amber-950/60 text-amber-300 border-amber-700/60"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                    >
                      {isMatch ? "✓ MATCH" : isMixed ? "△ MIXED" : "✕ DISTINCT"}
                    </span>
                  </td>
                  <td className="py-2.5 font-mono font-semibold text-slate-300">
                    {coveragePct}%
                  </td>
                  <td className="py-2.5 text-slate-400 text-xs">
                    {g.note || "Common feature"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ExclusionList({
  exclusions = [],
  title = "WHY NOT GROUPED? (Structural Separations)",
}) {
  if (!exclusions || exclusions.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-800 pb-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
          {title}
        </h3>
        <span className="text-xs text-slate-400">
          Nearest separated families kept distinct
        </span>
      </div>

      <div className="space-y-3">
        {exclusions.map((e, idx) => {
          const simPct = Math.round((e.similarity ?? 0) * 100);
          return (
            <div
              key={idx}
              className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-2 text-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-slate-100 text-sm">
                    Separated from: {e.other_family_id}
                  </span>
                  <span className="rounded bg-rose-950/60 text-rose-300 border border-rose-700/60 px-2 py-0.5 text-[11px] font-semibold">
                    Not Merged
                  </span>
                </div>
                <div className="text-slate-400">
                  Pairwise structural similarity:{" "}
                  <span className="font-mono font-bold text-white">{simPct}%</span>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">{e.basis}</p>

              {e.differing_dimensions && e.differing_dimensions.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
                  <span className="text-slate-400 font-semibold text-[11px] uppercase">
                    Differing Dimensions:
                  </span>
                  {e.differing_dimensions.map((dim) => (
                    <span
                      key={dim}
                      className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-xs text-slate-200"
                    >
                      {label(dim)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
