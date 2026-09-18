import { useState } from "react";

export default function PipelineBanner() {
  const [showExplanation, setShowExplanation] = useState(false);

  const steps = [
    {
      num: "1",
      title: "Narrative",
      sub: "Unstructured field text",
      detail: "Handles varied equipment, slang, and narrative styles without losing source text evidence spans.",
      color: "border-slate-700 bg-slate-900/80 text-slate-300",
      pill: "Raw Input",
    },
    {
      num: "2",
      title: "Safety Mechanism",
      sub: "Energy + Barrier + Phase",
      detail: "Extracts invariant physical controls (Energy Isolation, Pressurized Gas) independent of equipment keywords.",
      color: "border-sky-500/40 bg-sky-950/40 text-sky-200",
      pill: "Ontology Grounded",
    },
    {
      num: "3",
      title: "Barrier State",
      sub: "Strict Negation Engine",
      detail: "Deterministic syntactic parsing strictly separates Verified (intact) from Not Verified (omission) and Failed (hardware rupture).",
      color: "border-amber-500/40 bg-amber-950/40 text-amber-200",
      pill: "State Authoritative",
    },
    {
      num: "4",
      title: "Structural Family",
      sub: "Mechanism Clustering",
      detail: "Groups diverse stories (compressor, pump, flange) into the same Precursor Family while preserving state boundaries.",
      color: "border-indigo-500/40 bg-indigo-950/40 text-indigo-200",
      pill: "Precursor Engine",
    },
    {
      num: "5",
      title: "Recurrence",
      sub: "Early HSE Attention Signal",
      detail: "Surfaces systemic weak signals across multiple assets before an actual loss of containment or injury occurs.",
      color: "border-rose-500/40 bg-rose-950/40 text-rose-200",
      pill: "Proactive Defense",
    },
  ];

  return (
    <div className="rounded-xl border border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-3.5 shadow-lg shadow-black/40">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Core HSE Differentiator Pipeline
          </span>
          <span className="hidden sm:inline-block rounded bg-sky-500/10 px-2 py-0.5 text-[10px] font-mono text-sky-300 border border-sky-500/20">
            Deterministic Safety Intelligence
          </span>
        </div>
        <button
          type="button"
          onClick={() => setShowExplanation(!showExplanation)}
          className="text-xs font-mono text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-1 cursor-pointer"
        >
          <span>{showExplanation ? "Hide Architecture Flow ▲" : "How MECHORA Works ▼"}</span>
        </button>
      </div>

      {/* Stepper Pipeline Flow */}
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-5 relative">
        {steps.map((step, idx) => (
          <div
            key={step.title}
            className={`relative flex flex-col justify-between rounded-lg border p-2.5 transition-all ${step.color}`}
          >
            <div>
              <div className="flex items-center justify-between gap-1">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-800/90 text-[11px] font-bold text-slate-200 font-mono">
                  {step.num}
                </span>
                <span className="text-[9px] font-mono uppercase tracking-tight opacity-75">
                  {step.pill}
                </span>
              </div>
              <h3 className="mt-1.5 text-xs font-bold text-slate-100">{step.title}</h3>
              <p className="text-[10px] font-medium text-slate-400">{step.sub}</p>
            </div>

            {showExplanation && (
              <p className="mt-2 text-[10px] text-slate-400/90 border-t border-slate-800/60 pt-1.5 leading-relaxed">
                {step.detail}
              </p>
            )}

            {/* Arrow connector between steps (desktop) */}
            {idx < steps.length - 1 && (
              <div className="hidden sm:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-600 text-xs font-bold pointer-events-none">
                →
              </div>
            )}
          </div>
        ))}
      </div>

      {showExplanation && (
        <div className="mt-3 rounded-md border border-slate-800 bg-slate-950/70 p-2.5 text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-sky-300">
            Why this is NOT just an "LLM extracted fields + dashboard":
          </p>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Conventional NLP classifies observations by keywords (e.g. searching for "compressor" vs "flange"), which fragments the safety record into isolated silos. MECHORA abstracts away equipment-specific phrasing to identify the <strong>invariant physical barrier mechanism</strong> (e.g. Energy Isolation) and enforces <strong>deterministic barrier state negation</strong>. As a result, four differently worded reports across four different assets automatically collapse into a single recurring precursor family (PFAM-001), while verified positive checks and mechanical hardware failures are strictly preserved as separate mechanisms.
          </p>
        </div>
      )}
    </div>
  );
}
