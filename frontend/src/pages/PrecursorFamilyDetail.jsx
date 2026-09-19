import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  GitMerge,
  Layers,
  Activity,
  Sliders,
  Split,
  Check,
  Building2,
  Radio,
  Clock,
} from "lucide-react";
import { api, label } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge } from "../components/common/StatusBadge.jsx";
import { AttentionBar } from "../components/common/AttentionBar.jsx";
import { GroupingBreakdown, ExclusionList } from "../components/common/GroupingChips.jsx";

export default function PrecursorFamilyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [family, setFamily] = useState(null);
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("mechanism"); // mechanism | observations
  const [validationState, setValidationState] = useState(null); // 'confirmed' | 'resplit_requested' | null

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.family(id),
      api.observations({ family_id: id, limit: 50 }).catch(() => ({ observations: [] })),
    ])
      .then(([famData, obsData]) => {
        setFamily(famData);
        if (obsData?.observations && obsData.observations.length > 0) {
          setObservations(obsData.observations);
        } else if (famData?.observation_ids) {
          api.observations({ limit: 100 }).then((allObs) => {
            const matched = (allObs.observations || []).filter(
              (o) =>
                famData.observation_ids.includes(o.id) ||
                famData.observation_ids.includes(o.report_id),
            );
            setObservations(matched);
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="py-16 text-center text-xs text-slate-500 font-mono">
        Loading precursor family intelligence...
      </div>
    );
  }

  if (!family) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-12 text-center space-y-4">
        <h2 className="text-base font-bold text-white">Precursor Family Not Found</h2>
        <p className="text-xs text-slate-400">The requested precursor family identifier could not be located.</p>
        <Link to="/app/families" className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300">
          <ArrowLeft size={14} />
          <span>Return to Precursor Families</span>
        </Link>
      </div>
    );
  }

  const activities = family.activities || [];
  const locations = family.locations || [];
  const totalObs = family.observation_ids?.length || observations.length;

  return (
    <div className="space-y-6">
      {/* Standard Enterprise Page Header */}
      <PageHeader
        title={`${family.id} · ${family.name}`}
        subtitle={family.description}
        breadcrumbs={[
          { label: "Precursor Families", href: "/app/families" },
          { label: family.id },
        ]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StateBadge value={family.common_barrier_state} />
            <SIFBadge value={family.sif_potential_count > 0 ? "high" : "needs_review"} />
            {family.recurring && (
              <span className="rounded border border-rose-500/40 bg-rose-500/15 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-rose-300">
                Recurring Precursor ≥ {family.recurring_threshold || 2}
              </span>
            )}
          </div>
        }
      />

      {/* Summary KPI Cards & Attention Signal */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left 3 cols: Attention Signal breakdown */}
        <div className="lg:col-span-3 rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Radio size={16} className="text-amber-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">
                Precursor Attention Assessment
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-500">
              Deterministic Multi-Factor Scoring
            </span>
          </div>

          <AttentionBar
            value={family.attention_signal}
            showBasis={true}
            basis={family.attention_basis}
          />
        </div>

        {/* Right col: Portfolio Context KPIs */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 flex flex-col justify-between space-y-4">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
              Portfolio Footprint
            </span>
            <div className="mt-2 text-3xl font-black text-white font-mono">
              {totalObs}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Linked observation reports
            </p>
          </div>

          <div className="space-y-2 pt-3 border-t border-slate-800 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Distinct Activities</span>
              <span className="font-mono font-bold text-slate-200">{activities.length || 1}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Locations / Units</span>
              <span className="font-mono font-bold text-slate-200">{locations.length || "Refinery-wide"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">SIF Precursor Flag</span>
              <span className="font-semibold text-rose-400">
                {family.sif_potential_count > 0 ? `${family.sif_potential_count} Flagged` : "Under Review"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* CORE MECHANISM PANEL */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} className="text-amber-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-white">
              Core Barrier Breakdown Mechanism
            </h2>
          </div>
          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
            Canonical Structural Signature
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
              Hazardous Energy
            </span>
            <div className="mt-1 text-sm font-bold text-white capitalize">
              {label(family.common_energy)}
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              {family.hazard || "Pressurized hazardous energy source"}
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
              Required Safety Barrier
            </span>
            <div className="mt-1 text-sm font-bold text-white capitalize">
              {label(family.common_barrier)}
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Primary engineered or procedural control
            </p>
          </div>

          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-rose-300 block">
              Authoritative Barrier State
            </span>
            <div className="mt-1.5">
              <StateBadge value={family.common_barrier_state} />
            </div>
            <p className="mt-1.5 text-[11px] text-rose-300/80">
              Shared breakdown state across observations
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
              Exposure Mechanism
            </span>
            <div className="mt-1 text-sm font-bold text-white capitalize">
              {label(family.common_exposure)}
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Direct worker or asset exposure pathway
            </p>
          </div>
        </div>
      </div>

      {/* CROSS-EQUIPMENT CONVERGENCE DIAGRAM */}
      <div className="rounded-xl border border-amber-500/30 bg-slate-900/80 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <GitMerge size={16} className="text-amber-400" />
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">
                Cross-Equipment Structural Convergence
              </h2>
              <p className="text-[11px] text-slate-400">
                How disparate refinery units converge onto the exact same failure mechanism
              </p>
            </div>
          </div>
          <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold text-amber-300">
            Core Thesis (PS SIH26165)
          </span>
        </div>

        {/* Diagram Flow Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-center">
          {/* Column 1: Disparate Operational Contexts */}
          <div className="space-y-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
              <span>1. Disparate Contexts & Equipment</span>
            </span>
            <div className="space-y-2">
              {observations.slice(0, 3).map((obs, idx) => (
                <div
                  key={obs.id || idx}
                  className="rounded-lg border border-slate-800 bg-slate-950/90 p-2.5 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-slate-300">
                      {obs.report_id}
                    </span>
                    <span className="text-[10px] uppercase font-semibold text-amber-400">
                      {label(obs.event?.activity || "Maintenance")}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 italic">
                    "{obs.narrative}"
                  </p>
                </div>
              ))}
              {observations.length === 0 && (
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-500 italic">
                  Multiple distinct equipment and activity records
                </div>
              )}
            </div>
          </div>

          {/* Column 2: Shared Structural Mechanism */}
          <div className="relative rounded-lg border border-amber-500/40 bg-slate-950 p-4 space-y-3">
            <div className="text-[10px] uppercase font-bold tracking-wider text-amber-400 flex items-center justify-between">
              <span>2. Shared Structural Breakdown</span>
              <ShieldAlert size={14} />
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-400">Barrier</span>
                <span className="font-bold text-white capitalize">{label(family.common_barrier)}</span>
              </div>
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                <span className="text-slate-400">Breakdown State</span>
                <StateBadge value={family.common_barrier_state} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Energy Vector</span>
                <span className="font-bold text-white capitalize">{label(family.common_energy)}</span>
              </div>
            </div>
            <div className="text-[10px] text-slate-400 bg-slate-900/80 rounded p-2 text-center">
              Wordings differ, but the barrier vulnerability is identical.
            </div>
          </div>

          {/* Column 3: Precursor Alert Outcome */}
          <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-4 space-y-3">
            <div className="text-[10px] uppercase font-bold tracking-wider text-rose-300 flex items-center justify-between">
              <span>3. Aggregated Precursor Family</span>
              <AlertTriangle size={14} />
            </div>
            <div className="space-y-1.5">
              <div className="font-bold text-white text-sm">{family.id}</div>
              <p className="text-xs text-slate-300 leading-snug">
                Systemic recurrence pattern exposed before a major Loss of Containment event occurs.
              </p>
            </div>
            <div className="pt-2 border-t border-rose-500/20 flex items-center justify-between text-xs">
              <span className="text-rose-300/80">Recurrence Threshold</span>
              <span className="font-mono font-bold text-white">
                {family.recurring
                  ? `${totalObs} ≥ ${family.recurring_threshold || 2}`
                  : `${totalObs} observation${totalObs === 1 ? "" : "s"} · recurrence not established`}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* DETAIL TABS */}
      <div className="space-y-4">
        <div className="flex border-b border-slate-800 gap-6 text-xs font-bold">
          <button
            type="button"
            onClick={() => setActiveTab("mechanism")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "mechanism"
                ? "border-amber-500 text-amber-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitMerge size={14} />
            <span>WHY GROUPED? & WHY NOT GROUPED?</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("observations")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "observations"
                ? "border-amber-500 text-amber-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers size={14} />
            <span>Linked Observations</span>
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
              {observations.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Mechanism & Explainability */}
        {activeTab === "mechanism" && (
          <div className="space-y-6">
            {/* WHY GROUPED */}
            <GroupingBreakdown
              evidence={family.grouping_evidence}
              title={
                family.recurring
                  ? "WHY THESE REPORTS FORM ONE PRECURSOR PATTERN"
                  : "WHY THIS REPORT QUALIFIES AS A PRECURSOR CANDIDATE"
              }
              subtitle={
                family.recurring
                  ? "Per-dimension comparison over family members"
                  : "Single-report structural profile"
              }
            />

            {/* WHY NOT GROUPED */}
            <ExclusionList exclusions={family.exclusions} />
          </div>
        )}

        {/* Tab 2: Linked Observations Data Table */}
        {activeTab === "observations" && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden">
            {observations.length === 0 ? (
              <div className="p-12 text-center text-xs text-slate-500">
                No observations currently loaded for this family.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      <th className="px-4 py-3">Report ID</th>
                      <th className="px-4 py-3">Activity</th>
                      <th className="px-4 py-3">Energy / Hazard</th>
                      <th className="px-4 py-3">Barrier State</th>
                      <th className="px-4 py-3">SIF Potential</th>
                      <th className="px-4 py-3">Narrative Excerpt</th>
                      <th className="px-4 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {observations.map((obs) => {
                      const event = obs.event || {};
                      return (
                        <tr
                          key={obs.id}
                          className="hover:bg-slate-800/40 transition-colors group"
                        >
                          <td className="px-4 py-3 font-mono font-bold text-white whitespace-nowrap">
                            {obs.report_id || obs.id}
                          </td>
                          <td className="px-4 py-3 capitalize text-slate-300 whitespace-nowrap">
                            {label(event.activity || "Operations")}
                          </td>
                          <td className="px-4 py-3 capitalize text-slate-300 whitespace-nowrap">
                            {label(event.energy || family.common_energy)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <StateBadge value={event.barrier_state || family.common_barrier_state} />
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <SIFBadge value={event.sif?.classification || "needs_review"} />
                          </td>
                          <td className="px-4 py-3 text-slate-400 max-w-xs truncate">
                            {obs.narrative}
                          </td>
                          <td className="px-4 py-3 text-right whitespace-nowrap">
                            <Link
                              to={`/app/observations/${obs.id}`}
                              className="inline-flex items-center gap-1 font-semibold text-amber-400 hover:text-amber-300 hover:underline"
                            >
                              <span>Inspect</span>
                              <ArrowRight size={13} />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* HSE Human Validation Actions Footer */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-xs font-bold text-white block">
            HSE Expert Governance
          </span>
          <span className="text-[11px] text-slate-400">
            Confirm the grouping boundary of this precursor family or request deterministic re-split.
          </span>
        </div>

        <div className="flex items-center gap-2">
          {validationState === "confirmed" ? (
            <span className="flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-300">
              <Check size={14} />
              <span>Grouping Confirmed by HSE</span>
            </span>
          ) : validationState === "resplit_requested" ? (
            <span className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3.5 py-1.5 text-xs font-semibold text-amber-300">
              <Split size={14} />
              <span>Re-split Flagged for Next Pipeline Pass</span>
            </span>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setValidationState("confirmed")}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-500 transition-colors shadow-sm"
              >
                <Check size={14} />
                <span>Confirm Family</span>
              </button>
              <button
                type="button"
                onClick={() => setValidationState("resplit_requested")}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-600 transition-colors"
              >
                <Split size={14} />
                <span>Request Re-split</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
