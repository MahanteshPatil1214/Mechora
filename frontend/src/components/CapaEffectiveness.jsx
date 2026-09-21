import React from "react";
import { Link } from "react-router-dom";
import {
  ClipboardCheck,
  ArrowRight,
  RotateCcw,
  TrendingDown,
  Eye,
  FileQuestion,
} from "lucide-react";
import {
  label,
  capaStatusLabel,
  effectivenessStatusLabel,
  EFFECTIVENESS_STYLES,
  CAPA_STATUS_STYLES,
} from "../api.js";

// Reused verdict badge — same terminology and styles as the CAPA pages, so the
// dashboard surfaces exactly the existing language: RECURRENCE DETECTED,
// EVIDENCE OF IMPROVEMENT, UNDER OBSERVATION, INSUFFICIENT EVIDENCE.
export function EffectivenessBadge({ status, className = "", children }) {
  const norm =
    status && EFFECTIVENESS_STYLES[status]
      ? status
      : "insufficient_evidence";
  const cls = EFFECTIVENESS_STYLES[norm] || EFFECTIVENESS_STYLES.insufficient_evidence;
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${cls} ${className}`}
    >
      {children}
      {effectivenessStatusLabel(norm)}
    </span>
  );
}

export function CapaStatusBadge({ status, className = "" }) {
  const norm = status && CAPA_STATUS_STYLES[status] ? status : "open";
  const cls = CAPA_STATUS_STYLES[norm] || CAPA_STATUS_STYLES.open;
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${cls} ${className}`}
    >
      {capaStatusLabel(norm)}
    </span>
  );
}

export const EFF_SIGNAL_ICONS = {
  recurrence_detected: RotateCcw,
  improvement_observed: TrendingDown,
  under_observation: Eye,
  insufficient_evidence: FileQuestion,
};

// Compact single-card CAPA Effectiveness signal for the main dashboard.
// Surfaces the single most important CAPA verdict plus its barrier, the
// post-CAPA recurrence evidence and a direct link to the CAPA record.
export function CapaInsightCard({ signal, barrierCount = 0 }) {
  if (!signal) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ClipboardCheck size={15} className="text-amber-400" />
          <div>
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
              CAPA Effectiveness
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              No CAPA linked yet — create one from the CAPA page to start tracking effectiveness.
            </div>
          </div>
        </div>
        <Link
          to="/app/capas"
          className="flex items-center gap-1 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:underline flex-shrink-0"
        >
          <span>View CAPAs</span>
          <ArrowRight size={12} />
        </Link>
      </div>
    );
  }

  const Icon = EFF_SIGNAL_ICONS[signal.effectiveness_status] || ClipboardCheck;
  const recurrences = signal.post_capa?.recurrence_count ?? 0;
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider text-slate-400">
          <ClipboardCheck size={13} className="text-amber-400" />
          <span>CAPA Effectiveness</span>
        </span>
        {barrierCount > 1 && (
          <span className="font-mono text-[10px] text-slate-500">
            {barrierCount} CAPAs linked
          </span>
        )}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <EffectivenessBadge status={signal.effectiveness_status} className="gap-1.5 px-2.5 py-1 text-xs">
          <Icon size={13} />
        </EffectivenessBadge>
        <div className="min-w-0">
          <div className="text-sm font-bold text-white capitalize leading-tight">
            {label(signal.linked_barrier_id)}
          </div>
          <div className="text-xs text-slate-400">
            {recurrences} post-CAPA recurrence{recurrences === 1 ? "" : "s"}
            {signal.post_capa?.observation_ids?.length
              ? ` · ${signal.post_capa.observation_ids.length} post-closure obs`
              : ""}
          </div>
        </div>
        <Link
          to={`/app/capas/${signal.id}`}
          className="mt-1 sm:mt-0 sm:ml-auto flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:underline flex-shrink-0"
        >
          <span>View CAPA</span>
          <ArrowRight size={13} />
        </Link>
      </div>
    </div>
  );
}

// Compact per-barrier strip for the Precursor Families (barrier/overview) page.
// Shows how many CAPAs target this barrier's mechanism plus which effectiveness
// verdicts are present — or a quiet "No CAPA linked" state.
export function CapaInsightStrip({ barrier, summary }) {
  if (!summary || summary.total === 0) {
    return (
      <div className="rounded border border-dashed border-slate-800 px-3 py-2 text-[11px] text-slate-500">
        No CAPA linked to this barrier
      </div>
    );
  }

  const verdictChips = [
    {
      key: "recurrence_detected",
      count: summary.recurrenceDetected,
      label: "Recurrence",
      cls: "border-rose-500/40 bg-rose-500/10 text-rose-300",
    },
    {
      key: "improvement_observed",
      count: summary.improvementObserved,
      label: "Improvement",
      cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    },
    {
      key: "under_observation",
      count: summary.underObservation,
      label: "Under obs.",
      cls: "border-amber-500/40 bg-amber-500/10 text-amber-300",
    },
    {
      key: "insufficient_evidence",
      count: summary.insufficientEvidence,
      label: "No evidence",
      cls: "border-slate-700 bg-slate-900 text-slate-400",
    },
  ].filter((c) => c.count > 0);

  return (
    <div className="rounded border border-slate-800 bg-slate-950 px-3 py-2 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider text-slate-400">
          <ClipboardCheck size={11} className="text-amber-400" />
          <span>CAPA / Effectiveness</span>
        </span>
        <span className="font-mono text-[10px] text-slate-400">
          {summary.total} linked · {summary.open} open · {summary.closed} closed
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {verdictChips.map((c) => (
          <span
            key={c.key}
            className={`rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${c.cls}`}
          >
            {c.label} · {c.count}
          </span>
        ))}
        {summary.latest && (
          <Link
            to={`/app/capas/${summary.latest.id}`}
            className="ml-auto flex items-center gap-1 text-[11px] font-semibold text-amber-400 hover:text-amber-300 hover:underline"
          >
            <span>View CAPA</span>
            <ArrowRight size={11} />
          </Link>
        )}
      </div>
    </div>
  );
}

// Full evidence-based CAPA / Effectiveness section for the family (barrier)
// detail page: linked CAPA count, latest CAPA status, effectiveness verdict,
// post-CAPA recurrence count and affected sites, with a link into the CAPA.
export function CapaEffectivenessSection({ barrier, summary }) {
  const latest = summary?.latest || null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ClipboardCheck size={16} className="text-amber-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-white">
            CAPA / Effectiveness
          </h2>
        </div>
        <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
          {barrier ? label(barrier) : "Linked Barrier"}
        </span>
      </div>

      {!summary || summary.total === 0 ? (
        <p className="text-[11px] italic text-slate-500">
          No CAPA linked to this family's barrier yet. Create a CAPA targeting{" "}
          {barrier ? label(barrier) : "this barrier"} to begin effectiveness
          tracking.
        </p>
      ) : (
        <div className="space-y-4">
          {/* Portfolio counts */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                CAPA Count
              </div>
              <div className="mt-1 font-mono text-xl font-black text-white">
                {summary.total}
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                Open
              </div>
              <div className="mt-1 font-mono text-xl font-black text-sky-300">
                {summary.open}
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                Closed
              </div>
              <div className="mt-1 font-mono text-xl font-black text-emerald-300">
                {summary.closed}
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
                Post-CAPA Recurrences
              </div>
              <div
                className={`mt-1 font-mono text-xl font-black ${
                  (latest?.post_capa?.recurrence_count ?? 0) > 0
                    ? "text-rose-400"
                    : "text-emerald-400"
                }`}
              >
                {latest?.post_capa?.recurrence_count ?? 0}
              </div>
            </div>
          </div>

          {/* Verdict tally chips */}
          {[
            {
              key: "recurrence_detected",
              count: summary.recurrenceDetected,
              label: "Recurrence Detected",
              cls: "border-rose-500/40 bg-rose-500/10 text-rose-300",
            },
            {
              key: "improvement_observed",
              count: summary.improvementObserved,
              label: "Evidence of Improvement",
              cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
            },
            {
              key: "under_observation",
              count: summary.underObservation,
              label: "Under Observation",
              cls: "border-amber-500/40 bg-amber-500/10 text-amber-300",
            },
            {
              key: "insufficient_evidence",
              count: summary.insufficientEvidence,
              label: "Insufficient Evidence",
              cls: "border-slate-700 bg-slate-900 text-slate-400",
            },
          ]
            .filter((c) => c.count > 0)
            .map((c) => (
              <span
                key={c.key}
                className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${c.cls}`}
              >
                {c.label} · {c.count}
              </span>
            ))}
        </div>
      )}

      {latest && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-2.5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link
                to={`/app/capas/${latest.id}`}
                className="font-mono text-xs font-bold text-white hover:text-amber-400 transition-colors"
              >
                {latest.report_id}
              </Link>
              <div className="text-[11px] text-slate-400 truncate mt-0.5">
                {latest.title}
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <CapaStatusBadge status={latest.status} />
              <EffectivenessBadge status={latest.effectiveness_status} />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Status
              </span>
              <span className="font-semibold text-slate-200 capitalize">
                {capaStatusLabel(latest.status)}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Verdict
              </span>
              <span className="font-semibold text-slate-200 capitalize">
                {effectivenessStatusLabel(latest.effectiveness_status)}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Recurrences
              </span>
              <span
                className={`font-mono font-bold ${
                  (latest.post_capa?.recurrence_count ?? 0) > 0
                    ? "text-rose-400"
                    : "text-emerald-400"
                }`}
              >
                {latest.post_capa?.recurrence_count ?? 0}
              </span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Affected Sites
              </span>
              <span className="font-mono font-bold text-slate-200">
                {latest.baseline?.affected_sites ?? 0}
              </span>
            </div>
          </div>

          <div className="pt-1 border-t border-slate-800/70 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
              CAPA → Closure → Evidence → Verdict
            </span>
            <Link
              to={`/app/capas/${latest.id}`}
              className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:underline"
            >
              <span>View CAPA</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}