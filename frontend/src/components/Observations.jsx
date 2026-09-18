import { useEffect, useState } from "react";
import { api, label } from "../api.js";
import { Field, StateBadge, SIFBadge, NeedsReviewBadge, EvidenceChips, FamilyTypeBadge } from "./Badge.jsx";

function potentialBasis(event) {
  if (!event || event.potential_consequence_basis !== "model_inference") return "";
  const parts = [];
  if (event.barrier && event.barrier !== "unknown") parts.push(`${label(event.barrier)} (${label(event.barrier_state)})`);
  if (event.energy && event.energy !== "unknown") parts.push(label(event.energy));
  if (event.exposure && event.exposure !== "unknown") parts.push(label(event.exposure));
  return parts.join(" + ");
}

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
        {rows.map((o) => {
          const derivedType =
            o.event.barrier_state === "verified"
              ? "controlled"
              : o.event.needs_review || o.event.barrier_state === "unknown"
              ? "needs_review"
              : "precursor";

          return (
            <div key={o.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs text-slate-400">
                  {o.report_id} · {o.id}
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {o.event?.needs_review && (
                    <NeedsReviewBadge missingFields={o.event.missing_fields} />
                  )}
                  <FamilyTypeBadge type={derivedType} />
                  <StateBadge value={o.event.barrier_state} />
                  <SIFBadge value={o.event.sif.classification} />
                  <span className="text-[10px] font-mono text-slate-500">
                    conf {Number(o.event.sif.confidence ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>
            <p className="mt-2 line-clamp-2 text-sm text-slate-300">{o.narrative}</p>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              {(() => {
                const fb = o.event.field_basis || {};
                return [
                  <Field
                    key="activity"
                    name="Activity"
                    value={o.event.activity}
                    evidence={o.event.field_evidence?.activity}
                    basis={fb.activity}
                  />,
                  <Field
                    key="phase"
                    name="Task Phase"
                    value={o.event.task_phase}
                    evidence={o.event.field_evidence?.task_phase}
                    basis={fb.task_phase}
                  />,
                  <Field
                    key="energy"
                    name="Energy / Hazard"
                    value={o.event.energy}
                    evidence={o.event.field_evidence?.energy}
                    basis={fb.energy}
                  />,
                  <Field
                    key="barrier"
                    name="Barrier"
                    value={o.event.barrier}
                    evidence={o.event.field_evidence?.barrier}
                    basis={fb.barrier}
                  />,
                  <Field
                    key="exposure"
                    name="Exposure"
                    value={o.event.exposure}
                    evidence={o.event.field_evidence?.exposure}
                    basis={fb.exposure}
                  />,
                  <Field
                    key="potential"
                    name="Potential"
                    value={o.event.potential_consequence}
                    evidence={o.event.field_evidence?.potential_consequence}
                    basis={o.event.potential_consequence_basis}
                    basisDetail={potentialBasis(o.event)}
                  />,
                  <Field
                    key="actual"
                    name="Actual"
                    value={o.event.actual_consequence}
                    evidence={o.event.field_evidence?.actual_consequence}
                    basis={fb.actual_consequence}
                  />,
              <div className="flex flex-col gap-1 rounded-md border border-slate-800/80 bg-slate-900/60 p-2 min-w-[140px]">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Family
                  </span>
                  <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-500 lowercase">
                    cluster
                  </span>
                </div>
                <span className="text-sm font-semibold">
                  {o.precursor_family_id && o.precursor_family_id !== "UNASSIGNED / PENDING REVIEW" ? (
                    <span className="text-sky-300 font-mono">{o.precursor_family_id}</span>
                  ) : (
                    <span className="rounded bg-amber-500/15 border border-amber-500/40 px-1.5 py-0.5 text-[10px] text-amber-300 font-mono font-semibold">
                      UNASSIGNED / PENDING REVIEW
                    </span>
                  )}
                </span>
                <span className="text-[10px] text-slate-400">
                  State: <span className="font-semibold text-slate-200">{label(o.event.barrier_state)}</span>
                </span>
              </div>,
              ];
            })()}
            </div>
          </div>
        );
      })}
      </div>
    </div>
  );
}