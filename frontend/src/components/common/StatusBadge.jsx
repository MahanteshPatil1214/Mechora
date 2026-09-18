import React from "react";
import { STATE_GLYPHS, label } from "../../api.js";

// Clean, restrained semantic styling — no neon, no pulsing animations
export const STATE_STYLES = {
  verified: "bg-emerald-950/60 text-emerald-300 border-emerald-700/60",
  not_verified: "bg-rose-950/60 text-rose-300 border-rose-700/60",
  failed: "bg-rose-950/60 text-rose-300 border-rose-700/60",
  absent: "bg-rose-950/60 text-rose-300 border-rose-700/60",
  partially_effective: "bg-amber-950/60 text-amber-300 border-amber-700/60",
  unknown: "bg-slate-900 text-slate-400 border-slate-700/60",
};

export const SIF_STYLES = {
  high: "bg-rose-950/70 text-rose-200 border-rose-600/70",
  medium: "bg-amber-950/70 text-amber-200 border-amber-600/70",
  low: "bg-emerald-950/70 text-emerald-200 border-emerald-600/70",
  needs_review: "bg-sky-950/70 text-sky-200 border-sky-600/70",
};

export const VALIDATION_STYLES = {
  pending: "bg-amber-950/50 text-amber-300 border-amber-700/50",
  validated: "bg-emerald-950/50 text-emerald-300 border-emerald-700/50",
  rejected: "bg-rose-950/50 text-rose-300 border-rose-700/50",
};

export function StateBadge({ value, className = "" }) {
  const norm = (value || "unknown").toLowerCase();
  const cls = STATE_STYLES[norm] || STATE_STYLES.unknown;
  const glyph = STATE_GLYPHS[norm] || "?";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-semibold tracking-wide ${cls} ${className}`}
      title={`Barrier State: ${label(norm)}`}
    >
      <span className="font-bold text-[11px]">{glyph}</span>
      <span>{label(norm).toUpperCase()}</span>
    </span>
  );
}

export function SIFBadge({ value, className = "" }) {
  const norm = (value || "needs_review").toLowerCase();
  const cls = SIF_STYLES[norm] || SIF_STYLES.needs_review;

  const displayLabel =
    norm === "high"
      ? "HIGH SIF POTENTIAL"
      : norm === "medium"
      ? "MEDIUM SIF"
      : norm === "low"
      ? "LOW SIF"
      : "NEEDS REVIEW";

  return (
    <span
      className={`inline-flex items-center rounded border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${cls} ${className}`}
      title={`SIF Potential Classification: ${norm}`}
    >
      {displayLabel}
    </span>
  );
}

export function ValidationBadge({ status, className = "" }) {
  const norm = (status || "pending").toLowerCase();
  const cls = VALIDATION_STYLES[norm] || VALIDATION_STYLES.pending;
  const glyph = norm === "validated" ? "✓" : norm === "rejected" ? "✕" : "⏳";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-medium uppercase tracking-wider ${cls} ${className}`}
    >
      <span>{glyph}</span>
      <span>{norm}</span>
    </span>
  );
}

export function FieldItem({
  label: fieldLabel,
  value,
  source = "canonical",
  evidence = null,
  highlight = false,
}) {
  const displayVal = label(value);
  const isUnknown = !value || value === "unknown";

  return (
    <div
      className={`rounded border p-2.5 ${
        highlight
          ? "border-amber-500/40 bg-amber-950/20"
          : "border-slate-800 bg-slate-950/50"
      }`}
    >
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400 font-medium mb-1">
        <span>{fieldLabel}</span>
        {source === "inferred" && (
          <span className="text-[10px] text-sky-400 font-mono">
            inferred
          </span>
        )}
        {source === "grounded" && (
          <span className="text-[10px] text-emerald-400 font-mono">
            explicit
          </span>
        )}
      </div>

      <div
        className={`text-xs font-semibold ${
          isUnknown ? "italic text-slate-500" : "text-slate-200 capitalize"
        }`}
      >
        {isUnknown ? "Not Stated / Unknown" : displayVal}
      </div>

      {evidence && (
        <div className="mt-1.5 text-[11px] text-slate-400 border-t border-slate-800/60 pt-1">
          <span className="italic text-slate-300 font-mono">“{evidence}”</span>
        </div>
      )}
    </div>
  );
}
