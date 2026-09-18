import React from "react";
import { label } from "../../api.js";

export function HighlightedNarrative({
  narrative,
  fieldEvidence = {},
  className = "",
}) {
  if (!narrative) return null;

  // Extract all non-empty evidence spans
  const entries = Object.entries(fieldEvidence || {})
    .filter(([, val]) => typeof val === "string" && val.trim().length > 0)
    .map(([field, span]) => ({
      field,
      span: span.trim(),
    }));

  if (entries.length === 0) {
    return (
      <p className={`text-sm sm:text-base leading-relaxed text-slate-200 ${className}`}>
        {narrative}
      </p>
    );
  }

  let segments = [{ text: narrative, field: null }];

  for (const { field, span } of entries) {
    const nextSegments = [];
    for (const seg of segments) {
      if (seg.field) {
        nextSegments.push(seg);
        continue;
      }

      const idx = seg.text.toLowerCase().indexOf(span.toLowerCase());
      if (idx === -1) {
        nextSegments.push(seg);
      } else {
        const before = seg.text.slice(0, idx);
        const match = seg.text.slice(idx, idx + span.length);
        const after = seg.text.slice(idx + span.length);

        if (before) nextSegments.push({ text: before, field: null });
        nextSegments.push({ text: match, field });
        if (after) nextSegments.push({ text: after, field: null });
      }
    }
    segments = nextSegments;
  }

  return (
    <div className={`text-sm sm:text-base leading-relaxed text-slate-200 ${className}`}>
      {segments.map((seg, i) => {
        if (!seg.field) {
          return <span key={i}>{seg.text}</span>;
        }

        return (
          <mark
            key={i}
            className="rounded border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.5 font-medium text-amber-200 mx-0.5"
            title={`Evidence for ${label(seg.field)}`}
          >
            {seg.text}
            <span className="ml-1 text-[11px] uppercase font-bold text-amber-400">
              [{label(seg.field)}]
            </span>
          </mark>
        );
      })}
    </div>
  );
}

export function EvidenceChipsList({ fieldEvidence }) {
  if (!fieldEvidence) return null;
  const entries = Object.entries(fieldEvidence).filter(([, v]) => v);
  if (!entries.length) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
      {entries.map(([k, v]) => (
        <div
          key={k}
          className="flex items-start justify-between gap-2 rounded border border-slate-800 bg-slate-900/90 p-2"
        >
          <span className="font-semibold text-slate-400 uppercase text-[11px]">
            {k.replace(/_/g, " ")}:
          </span>
          <span className="font-mono text-slate-200 text-right">“{v}”</span>
        </div>
      ))}
    </div>
  );
}
