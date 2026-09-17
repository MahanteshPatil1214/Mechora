import { STATE_COLORS, SIF_COLORS, label } from "../api.js";

export function StateBadge({ value }) {
  const cls = STATE_COLORS[value] || STATE_COLORS.unknown;
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label(value)}
    </span>
  );
}

export function SIFBadge({ value }) {
  const cls = SIF_COLORS[value] || SIF_COLORS.needs_review;
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-bold ${cls}`}>
      {value?.toUpperCase?.() ?? "—"}
    </span>
  );
}

export function Field({ name, value }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-widest text-slate-500">{name}</span>
      <span className="text-sm capitalize text-slate-100">{label(value)}</span>
    </div>
  );
}

export function SifPanel({ sif }) {
  if (!sif) return null;
  const pct = Math.round((sif.confidence ?? 0) * 100);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-widest text-slate-500">
          SIF potential
        </span>
        <div className="flex items-center gap-2">
          <SIFBadge value={sif.classification} />
          <span className="text-xs text-slate-400">{pct}%</span>
        </div>
      </div>
      <p className="mt-2 text-xs text-slate-300">{sif.reason}</p>
      {sif.supporting_evidence?.length ? (
        <ul className="mt-2 space-y-0.5">
          {sif.supporting_evidence.map((e, i) => (
            <li key={i} className="text-[11px] text-slate-400">· {e}</li>
          ))}
        </ul>
      ) : null}
      {sif.model_note ? (
        <p className="mt-2 text-[10px] italic text-slate-500">{sif.model_note}</p>
      ) : null}
    </div>
  );
}

export function EvidenceChips({ fieldEvidence }) {
  if (!fieldEvidence) return null;
  const entries = Object.entries(fieldEvidence).filter(([, v]) => v);
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([k, v]) => (
        <span
          key={k}
          className="rounded-md border border-slate-700/70 bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-400"
        >
          <span className="font-semibold text-slate-500">{k.replace(/_/g, " ")}:</span> “{v}”
        </span>
      ))}
    </div>
  );
}