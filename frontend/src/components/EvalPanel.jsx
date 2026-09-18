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
        <div className="mt-3 rounded-md border border-slate-800 bg-slate-950/60 p-2.5 text-[11px] space-y-1.5">
          <p className="font-semibold text-slate-300 flex items-center gap-1.5">
            <span className="text-sky-400">ℹ</span> Benchmark transparency
          </p>
          <ul className="space-y-1 text-slate-400">
            <li className="flex items-start gap-1.5">
              <span className="text-sky-400 font-bold">•</span>
              Total benchmark set: n={data.metrics.record_count ?? data.counts?.records ?? 216} frozen records
            </li>
            <li className="flex items-start gap-1.5">
              <span className="text-sky-400 font-bold">•</span>
              Rule-based / deterministic benchmark (ontology + negation engine; no LLM randomness)
            </li>
            <li className="flex items-start gap-1.5">
              <span className="text-sky-400 font-bold">•</span>
              Synthetic / representative sample data — not live operational field data
            </li>
            <li className="flex items-start gap-1.5">
              <span className="text-amber-400 font-bold">•</span>
              NOT OIL production accuracy — not an official corporate risk score
            </li>
            <li className="flex items-start gap-1.5">
              <span className="text-amber-400 font-bold">•</span>
              Not independently validated field performance
            </li>
          </ul>
          <p className="text-[10px] text-slate-500 italic pt-0.5">
            Offline verification benchmark · deterministic pipeline · frozen test set · no fabricated metrics.
          </p>
        </div>
      </div>
    </div>
  );
}