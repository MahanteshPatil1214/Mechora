import { useEffect, useState } from "react";
import { api, label } from "../api.js";
import { SIFBadge, StateBadge } from "./Badge.jsx";

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
                    recurring
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
          </div>
        ))}
      </div>
    </div>
  );
}