import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Flame,
  ShieldAlert,
  Layers,
  Network,
  CheckCircle,
  FileCheck2,
  Lock,
  GitMerge,
  Cpu,
  Activity,
  AlertOctagon,
  Eye,
  Sliders,
  Scale,
  ArrowDown,
  Check,
  Building2,
} from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-16 py-10 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto">
      {/* 1. HERO SECTION */}
      <section className="text-center pt-4 pb-8 max-w-4xl mx-auto space-y-5">
        <div className="inline-flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
          <Flame size={14} className="text-amber-400" />
          <span>Oil India Limited · Problem Statement SIH26165</span>
        </div>

        <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-white leading-tight">
          Structural Precursor Intelligence for Enterprise HSE
        </h1>

        <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
          MECHORA converts unstructured safety observations into canonical structured events and
          exposes recurring barrier breakdown mechanisms across disparate refinery equipment and operations.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            to="/login"
            className="flex items-center gap-2 rounded-lg bg-amber-500 px-5 py-2.5 text-xs font-bold text-slate-950 hover:bg-amber-400 transition-colors shadow-sm"
          >
            <span>Sign In to HSE Workspace</span>
            <ArrowRight size={14} />
          </Link>
          <a
            href="#mechanism-flow"
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-5 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <span>See Core Mechanism</span>
          </a>
        </div>

        <p className="text-xs italic text-slate-500 pt-1">
          Prototype HSE Attention Signal — decision support, not an official OIL risk score or accident prediction.
        </p>
      </section>

      {/* 2. THE 5-STEP CORE CONCEPT FLOW */}
      <section id="mechanism-flow" className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-1">
          <div className="text-xs font-bold uppercase tracking-widest text-amber-400">
            Mechanism Detection Pipeline
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-white">
            From Free-Text Stories to Systemic Precursors
          </h2>
          <p className="text-xs text-slate-400">
            We identify recurring safety mechanisms, not merely similar wording.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-2">
            <div className="text-[10px] font-mono font-bold text-amber-400 uppercase">Step 01</div>
            <h3 className="font-bold text-xs text-white">Different Safety Stories</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Unstructured frontline narratives recorded with disparate phrasing across various refinery units.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-2">
            <div className="text-[10px] font-mono font-bold text-sky-400 uppercase">Step 02</div>
            <h3 className="font-bold text-xs text-white">Structured Safety Events</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Extraction of Energy, Barrier, Barrier State, and Exposure with in-situ evidence grounding.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-2">
            <div className="text-[10px] font-mono font-bold text-indigo-400 uppercase">Step 03</div>
            <h3 className="font-bold text-xs text-white">Precursor Signature</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Canonical vector representation capturing the fundamental physical and procedural breakdown.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-2">
            <div className="text-[10px] font-mono font-bold text-rose-400 uppercase">Step 04</div>
            <h3 className="font-bold text-xs text-white">Recurring Precursor Families</h3>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Clustering reports sharing identical failure mechanisms while enforcing hard negation rules.
            </p>
          </div>

          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2">
            <div className="text-[10px] font-mono font-bold text-emerald-400 uppercase">Step 05</div>
            <h3 className="font-bold text-xs text-emerald-200">HSE Attention Signals</h3>
            <p className="text-[11px] text-emerald-300/80 leading-relaxed">
              Deterministic 0–100 attention scoring with full explainability: WHY GROUPED and WHY NOT GROUPED.
            </p>
          </div>
        </div>
      </section>

      {/* 3. REALISTIC REFINERY EXAMPLE & CONVERGENCE */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 space-y-6">
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-amber-400">
            The MECHORA Differentiator
          </div>
          <h2 className="mt-1 text-xl sm:text-2xl font-bold text-white">
            Cross-Equipment Mechanism Convergence
          </h2>
          <p className="mt-2 text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
            Different equipment. Different activities. Different words. Yet beneath the surface lies the
            exact same barrier breakdown:
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          {/* Left: 3 Surface Stories */}
          <div className="lg:col-span-5 space-y-2.5">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              Frontline Surface Narratives
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs space-y-1">
              <span className="font-bold text-amber-300">Unit 1 · Pipeline Flange Overhaul</span>
              <p className="text-slate-300 italic text-[11px]">
                “Fitter opened flange before line was proven depressurized; residual fluid splashed.”
              </p>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs space-y-1">
              <span className="font-bold text-amber-300">Unit 2 · Compressor Servicing</span>
              <p className="text-slate-300 italic text-[11px]">
                “Crew opened casing without zero-energy verification; gas release observed.”
              </p>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs space-y-1">
              <span className="font-bold text-amber-300">Unit 3 · Vessel Blowdown</span>
              <p className="text-slate-300 italic text-[11px]">
                “Zero-energy was never checked before the drain joint unbolted; leaking noticed.”
              </p>
            </div>
          </div>

          {/* Center Connector */}
          <div className="lg:col-span-2 flex flex-col items-center justify-center text-center py-2">
            <div className="h-9 w-9 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <GitMerge size={18} />
            </div>
            <span className="mt-1.5 text-[10px] font-bold uppercase tracking-wider text-amber-400">
              Converges into
            </span>
          </div>

          {/* Right: The Same Precursor Family */}
          <div className="lg:col-span-5">
            <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-rose-500/20 pb-2">
                <span className="rounded bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold uppercase text-rose-200">
                  Recurring Precursor Family
                </span>
                <span className="font-mono text-xs font-bold text-rose-300">PF-01</span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white">
                  Energy Isolation Verification Breakdown
                </h3>
                <p className="text-xs text-rose-200/80 mt-0.5">
                  High SIF-potential precursor pattern active across multiple operating units.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                <div className="rounded bg-slate-950/80 p-2 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Barrier</span>
                  <span className="font-semibold text-slate-200">Energy Isolation</span>
                </div>
                <div className="rounded bg-slate-950/80 p-2 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">State</span>
                  <span className="font-semibold text-rose-400">Not Verified</span>
                </div>
                <div className="rounded bg-slate-950/80 p-2 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Hazard</span>
                  <span className="font-semibold text-slate-200">Pressurized Gas</span>
                </div>
                <div className="rounded bg-slate-950/80 p-2 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">Attention</span>
                  <span className="font-mono font-bold text-amber-400">84.7 / 100</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. EXPLAINABILITY: WHY GROUPED / WHY NOT GROUPED */}
      <section className="space-y-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-amber-400">
            Explainable Engineering Rationale
          </div>
          <h2 className="mt-1 text-xl font-bold text-white">
            No Black Boxes — Complete Transparency
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5 space-y-2.5">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <CheckCircle size={15} />
              <span>WHY GROUPED? (Evidence Grounding)</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every member in a precursor family is evaluated across 7 structural dimensions: Energy, Barrier,
              Barrier State, Exposure, Task Phase, Activity, and Narrative alignment.
            </p>
            <div className="rounded border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-emerald-300 space-y-1">
              <div>✓ Energy: Pressurized Gas (100% agreement)</div>
              <div>✓ Barrier: Energy Isolation (100% agreement)</div>
              <div>✓ Barrier State: Not Verified (100% agreement)</div>
              <div>△ Activity: 4 distinct activities (Cross-equipment divergence)</div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5 space-y-2.5">
            <div className="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase tracking-wider">
              <AlertOctagon size={15} />
              <span>WHY NOT GROUPED? (Hard Rule Separation)</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Observations that fail different barriers or demonstrate verified compliance are explicitly
              kept separate rather than artificially grouped by superficial text similarity.
            </p>
            <div className="rounded border border-slate-800 bg-slate-950 p-2.5 text-xs font-mono text-rose-300 space-y-1">
              <div>✕ Excluded from Hot Work family: Lacks thermal/ignition source.</div>
              <div>✕ Hard Negation Rule: Verified compliance records never merge with failure families.</div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. HSE HUMAN GOVERNANCE CTA */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-1.5 rounded-md border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300">
          <Scale size={14} />
          <span>HSE Human-in-the-Loop Governance</span>
        </div>

        <h2 className="text-xl font-bold text-white">
          Engineered for Qualified HSE Professionals
        </h2>

        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
          MECHORA serves as an operational decision-support tool. It empowers Oil India Limited safety teams
          with deterministic barrier visibility, human-in-the-loop review queues, and grounded narrative evidence.
        </p>

        <div className="pt-2">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:bg-amber-400 transition-colors shadow-sm"
          >
            <span>Enter HSE Workspace</span>
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>
    </div>
  );
}
