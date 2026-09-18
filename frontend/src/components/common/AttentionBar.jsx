import React, { useState } from "react";

export const ATTENTION_DISCLAIMER =
  "Prototype HSE Attention Signal (0–100) — engineering decision support, not an official OIL risk score or accident prediction.";

export function AttentionBar({
  value,
  showBasis = false,
  basis = [],
  factors = [],
  compact = false,
  collapsible = true,
}) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const width = Math.round(v);

  const barColor =
    v >= 70
      ? "bg-rose-500"
      : v >= 40
      ? "bg-amber-500"
      : "bg-sky-500";

  const textColor =
    v >= 70 ? "text-rose-400" : v >= 40 ? "text-amber-400" : "text-sky-400";

  const factorList = basis?.length > 0 ? basis : (factors?.length > 0 ? factors : []);

  return (
    <div className="w-full space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
          Prototype Attention Signal
        </span>
        <span className={`font-mono font-bold text-xs ${textColor}`}>
          {v.toFixed(1)}{" "}
          <span className="text-[10px] text-slate-500 font-normal">/ 100</span>
        </span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800 border border-slate-700/50">
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${width}%` }}
        />
      </div>

      {showBasis && factorList.length > 0 && (
        <div className="text-[11px]">
          {collapsible ? (
            <details className="group mt-1">
              <summary className="cursor-pointer text-[11px] text-slate-400 hover:text-slate-200 font-medium py-0.5 list-none flex items-center gap-1 select-none">
                <span className="transition-transform group-open:rotate-90">▸</span>
                <span>View contributing factors ({factorList.length})</span>
              </summary>
              <ul className="mt-1 space-y-1 pl-3 text-slate-300 border-l border-slate-800">
                {factorList.map((item, idx) => (
                  <li key={idx} className="leading-tight text-[11px]">
                    {typeof item === "string" ? item : item.name || item.factor || JSON.stringify(item)}
                  </li>
                ))}
              </ul>
            </details>
          ) : (
            <ul className="mt-1 space-y-1 text-slate-300 pl-3 border-l border-slate-800">
              {factorList.map((item, idx) => (
                <li key={idx} className="leading-tight text-[11px]">
                  {typeof item === "string" ? item : item.name || item.factor || JSON.stringify(item)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {!compact && (
        <p className="text-[10px] italic text-slate-400 leading-snug">
          {ATTENTION_DISCLAIMER}
        </p>
      )}
    </div>
  );
}
