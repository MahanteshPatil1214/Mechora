import { useEffect, useState } from "react";
import { api, label } from "../api.js";
import { Field, StateBadge, SIFBadge, EvidenceChips } from "./Badge.jsx";

export default function Observations({ refreshKey }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [state, setState] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    try {
      const res = await api.observations({ barrier_state: state, limit: 25 });
      setRows(res.observations);
      setTotal(res.total);
      setErr("");
    } catch (e) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [state, refreshKey]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Observations <span className="ml-1 text-slate-600">({total})</span>
        </h2>
        <select
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs focus:border-sky-500 focus:outline-none"
        >
          <option value="">All states</option>
          {["verified", "not_verified", "failed", "absent", "partially_effective", "unknown"].map(
            (s) => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ),
          )}
        </select>
      </div>
      {err && (
        <p className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {err}
        </p>
      )}
      <div className="mt-3 space-y-2">
        {rows.map((o) => (
          <div key={o.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-400">
                {o.report_id} · {o.id}
              </span>
              <div className="flex items-center gap-2">
                <StateBadge value={o.event.barrier_state} />
                <SIFBadge value={o.event.sif.classification} />
                <span className="text-[10px] text-slate-500">
                  {Math.round((o.event.sif.confidence ?? 0) * 100)}%
                </span>
              </div>
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-slate-300">{o.narrative}</p>
            <div className="mt-3 grid grid-cols-3 gap-2 md:grid-cols-6">
              <Field name="Activity" value={o.event.activity} />
              <Field name="Energy" value={o.event.energy} />
              <Field name="Barrier" value={o.event.barrier} />
              <Field name="Exposure" value={o.event.exposure} />
              <Field name="Consequence" value={o.event.potential_consequence} />
              <span className="text-sm text-slate-500">
                {o.precursor_family_id ? (
                  <span className="text-sky-300">family {o.precursor_family_id}</span>
                ) : (
                  "unassigned"
                )}
              </span>
            </div>
            {o.event.field_evidence && (
              <div className="mt-2">
                <EvidenceChips fieldEvidence={o.event.field_evidence} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}