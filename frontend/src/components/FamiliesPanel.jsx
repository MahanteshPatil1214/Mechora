import { useEffect, useState } from "react";
import { api, label } from "../api.js";
import { SIFBadge, StateBadge } from "./Badge.jsx";

const ATTENTION_DISCLAIMER =
  "Prototype Precursor Attention Signal (0-100). Decision-support signal; not an official OIL risk score.";

const GE_GLYPH = { same: "✓", mixed: "△", distinct: "×" };
const GE_COLOR = {
  same: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  mixed: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  distinct: "border-slate-600 bg-slate-800/60 text-slate-300",
};

function AttentionBar({ value }) {
  const v = Math.max(0, Math.min(100, value));
  const width = Math.round(v);
  return (
    <div className="flex w-full items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${v >= 70 ? "bg-rose-500" : v >= 40 ? "bg-amber-500" : "bg-sky-500"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="w-14 text-right text-xs font-mono text-slate-300">{v.toFixed(1)}</span>
    </div>
  );
}

function GroupingChips({ evidence }) {
  if (!evidence?.length) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-emerald-400">
        Why grouped
      </div>
      <div className="mt-1 flex flex-wrap gap-1">
        {evidence.map((g) => (
          <span
            key={g.dimension}
            title={g.note || ""}
            className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] ${GE_COLOR[g.status] || GE_COLOR.distinct}`}
          >
            <span className="font-bold">{GE_GLYPH[g.status] || "·"}</span>
            <span className="capitalize text-slate-400">{label(g.dimension)}</span>
            <span className="font-medium">= {label(g.value)}</span>
            <span className="opacity-70">({Math.round((g.coverage ?? 0) * 100)}%)</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function ExclusionList({ exclusions }) {
  if (!exclusions?.length) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-slate-400">
        Why NOT grouped
      </div>
      <div className="mt-1 space-y-0.5">
        {exclusions.map((e, i) => (
          <div
            key={`${e.other_family_id}-${i}`}
            title={e.basis || ""}
            className="rounded-md border border-slate-700/70 bg-slate-900/70 px-2 py-1 text-[10px] text-slate-400"
          >
            vs <span className="font-mono text-slate-300">{e.other_family_id}</span>
            <span className="text-slate-500"> · sim {(e.similarity ?? 0) * 100}%</span>
            <span className="text-slate-500"> · differs </span>
            <span className="text-slate-300">
              {(e.differing_dimensions || []).map(label).join(", ")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FamiliesPanel() {
  const [rows, setRows] = useState([]);
  const [recOnly, setRecOnly] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.families(recOnly).then((res) => setRows(res.families)).catch((e) => setErr(e.message));
  }, [recOnly]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Precursor families
        </h2>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox"
            checked={recOnly}
            onChange={(e) => setRecOnly(e.target.checked)}
            className="accent-sky-500"
          />
          Recurring only
        </label>
      </div>
      {err && (
        <p className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {err}
        </p>
      )}
      <div className="mt-3 space-y-3">
        {rows.map((f) => (
          <div key={f.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <span className="text-sm font-semibold text-slate-100">{f.name}</span>
                {f.recurring && (
                  <span className="ml-2 rounded-md border border-rose-500/50 bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-rose-300">
                    recurring ≥ {f.recurring_threshold}
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500">{f.id}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400">{f.description}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <StateBadge value={f.common_barrier_state} />
              <span className="capitalize text-slate-300">{label(f.common_barrier)}</span>
              <span className="text-slate-500">·</span>
              <span className="capitalize text-slate-300">{label(f.common_energy)}</span>
              <span className="text-slate-500">·</span>
              <span className="text-slate-300">
                {f.sif_potential_count} SIF potential
              </span>
              <SIFBadge value={f.sif_potential_count > 0 ? "high" : "needs_review"} />
              <span className="ml-auto text-slate-500">{f.observation_ids.length} observations</span>
            </div>
            <div className="mt-2">
              <AttentionBar value={f.attention_signal} />
            </div>
            <div className="mt-1 space-y-0.5">
              {(f.attention_basis || []).map((b, i) => (
                <p key={i} className="text-[10px] text-slate-400">· {b}</p>
              ))}
            </div>
            <p className="mt-0.5 text-[10px] italic text-slate-600">{ATTENTION_DISCLAIMER}</p>
            <div className="mt-3 space-y-2">
              <GroupingChips evidence={f.grouping_evidence} />
              <ExclusionList exclusions={f.exclusions} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}