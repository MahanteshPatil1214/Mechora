import { useEffect, useState } from "react";
import { api, label } from "../api.js";

export default function EvalPanel() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .evaluation()
      .then((res) => setData(res))
      .catch((e) => setErr(e.message));
  }, []);

  if (err) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Evaluation
        </h2>
        <p className="mt-3 text-sm text-slate-500">No stored evaluation yet — run scripts/run_evaluation.py</p>
      </div>
    );
  }
  if (!data) return null;

  const fields = data.metrics.field_accuracy || {};
  const critical = data.metrics.critical_suite || {};

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Evaluation
        </h2>
        <span className="text-[11px] text-slate-500">
          {data.run_id} · n={data.metrics.record_count ?? data.counts?.records}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1.5 md:grid-cols-2">
        {Object.entries(fields).map(([k, v]) => (
          <div key={k} className="flex items-center justify-between text-xs">
            <span className="capitalize text-slate-400">{label(k)}</span>
            <span className="font-mono text-slate-200">{v.toFixed(3)}</span>
          </div>
        ))}
        {data.metrics.sif && (
          <div className="flex items-center justify-between text-xs">
            <span className="capitalize text-slate-400">SIF macro-F1</span>
            <span className="font-mono text-slate-200">
              {data.metrics.sif.macro_f1.toFixed(3)}
            </span>
          </div>
        )}
      </div>
      <div className="mt-3 border-t border-slate-800 pt-2">
        <div className="grid grid-cols-1 gap-x-6 gap-y-1.5 md:grid-cols-2">
          {Object.entries(critical).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{label(k)}</span>
              <span className="font-mono text-slate-200">
                {v.accuracy?.toFixed(3)} <span className="text-slate-600">(n={v.n})</span>
              </span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-[11px] italic text-slate-600">
          Deterministic rule pipeline · no fabricated metrics
        </p>
      </div>
    </div>
  );
}