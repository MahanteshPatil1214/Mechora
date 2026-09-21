import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, AlertTriangle, ClipboardCheck, Activity } from "lucide-react";
import { buildEvidenceChain } from "../api.js";
import { EffectivenessBadge } from "./CapaEffectiveness.jsx";

const TONE_FRAME = {
  rose: "border-rose-500/30 bg-rose-500/10",
  amber: "border-amber-500/30 bg-amber-500/10",
  sky: "border-sky-500/30 bg-sky-500/10",
  emerald: "border-emerald-500/30 bg-emerald-500/10",
  slate: "border-slate-700 bg-slate-900/60",
};

const STEP_ICONS = {
  failure: AlertTriangle,
  capa: ClipboardCheck,
  evidence: Activity,
  verdict: ClipboardCheck,
};

// One step of the Key Attention Area evidence chain. Titled generically so the
// step labels (Recurring Barrier Failure / CAPA Raised / Post-CAPA Evidence /
// Effectiveness Verdict) come straight from the shared builder.
function StepCard({ step, index, last }) {
  const Icon = STEP_ICONS[step.key] || ClipboardCheck;
  const inner = (
    <div
      className={`flex h-full flex-col rounded-lg border p-3.5 transition-colors ${
        TONE_FRAME[step.tone] || TONE_FRAME.slate
      } ${step.to ? "hover:brightness-110" : ""}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500">
          {index + 1} / {last + 1}
        </span>
        <Icon size={14} className="flex-shrink-0 text-slate-400" />
      </div>

      <div
        className={`mt-1.5 text-[10px] font-bold uppercase tracking-wider ${
          step.tone === "rose"
            ? "text-rose-300"
            : step.tone === "emerald"
              ? "text-emerald-300"
              : step.tone === "amber"
                ? "text-amber-300"
                : step.tone === "sky"
                  ? "text-sky-300"
                  : "text-slate-300"
        }`}
      >
        {step.label}
      </div>

      <div className="mt-1 text-sm font-bold leading-tight text-white">
        {step.status ? (
          <EffectivenessBadge status={step.status} />
        ) : (
          <span className="capitalize">{step.detail}</span>
        )}
      </div>

      {step.facts.length > 0 && (
        <ul className="mt-2 space-y-1 border-t border-slate-800/70 pt-2">
          {step.facts.map((fact) => (
            <li
              key={fact}
              className="flex items-start gap-1.5 text-[11px] leading-snug text-slate-300"
            >
              <span
                className={`mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  step.tone === "rose"
                    ? "bg-rose-400"
                    : step.tone === "emerald"
                      ? "bg-emerald-400"
                      : step.tone === "amber"
                        ? "bg-amber-400"
                        : step.tone === "sky"
                          ? "bg-sky-400"
                          : "bg-slate-500"
                }`}
              />
              <span>{fact}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  return (
    <React.Fragment>
      <div className="flex flex-1 min-w-0">{step.to ? <Link to={step.to} className="flex-1 min-w-0">{inner}</Link> : inner}</div>
      {!last && (
        <div className="hidden items-center flex-shrink-0 text-slate-600 lg:flex">
          <ArrowRight size={16} />
        </div>
      )}
    </React.Fragment>
  );
}

// The Key Attention Area evidence chain: the four-step story that makes the
// Observation -> Barrier Failure -> Precursor -> CAPA -> Post-CAPA Evidence ->
// Effectiveness loop visible on the Home page. Links deep into the relevant
// Precursor Family and CAPA records; every data point is projected live.
export default function EvidenceChain({ family, capa }) {
  const chain = buildEvidenceChain(family, capa);
  const steps = [chain.failure, chain.capa, chain.evidence, chain.verdict];

  return (
    <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
      {steps.map((step, i) => (
        <StepCard key={step.key} step={step} index={i} last={steps.length - 1} />
      ))}
    </div>
  );
}