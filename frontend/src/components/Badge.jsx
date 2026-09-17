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