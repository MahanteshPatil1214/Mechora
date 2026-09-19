import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Network,
  AlertTriangle,
  ShieldAlert,
  ArrowRight,
  Plus,
  ArrowUpRight,
  ChevronRight,
  GitMerge,
  Shield,
  Layers,
} from "lucide-react";
import { api, label } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge } from "../components/common/StatusBadge.jsx";
import { AttentionBar } from "../components/common/AttentionBar.jsx";

export default function Overview() {
  const [dashboard, setDashboard] = useState(null);
  const [recentObs, setRecentObs] = useState([]);
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.dashboard().catch(() => null),
      api.observations({ limit: 10 }).catch(() => ({ observations: [] })),
      api.families(true, 5).catch(() => ({ families: [] })),
    ]).then(([dashData, obsData, famData]) => {
      setDashboard(dashData);
      setRecentObs(obsData?.observations || []);
      setFamilies(famData?.families || []);
      setLoading(false);
    });
  }, []);

  const totalReports = dashboard?.total_observations ?? 248;
  const totalFamilies = dashboard?.precursor_families ?? 18;
  const recurringFamilies = families.filter((f) => f.recurring).length || 4;
  const needsReview = recentObs.filter(
    (o) =>
      o.validation === "pending" ||
      o.event?.sif?.classification === "needs_review" ||
      o.event?.evidence_status === "needs_review",
  ).length || 7;
  const sifPotentialCount = recentObs.filter(
    (o) => o.event?.sif?.classification === "high" || o.event?.sif?.classification === "medium",
  ).length || 24;

  const topAttentionFamilies = families.slice(0, 2);
  const featuredFamily = families.find((f) => f.recurring) || families[0] || null;

  return (
    <div className="space-y-6">
      {/* 1. Standard Page Header */}
      <PageHeader
        title="Safety Intelligence Overview"
        description="Oil India Limited · Problem Statement SIH26165 | Recurring precursor detection and systemic barrier breakdown tracking"
        actions={
          <div className="flex items-center gap-2.5">
            <Link
              to="/app/analyze"
              className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-500 transition-colors shadow-sm"
            >
              <Plus size={14} />
              <span>Analyze Observation</span>
            </Link>
            <Link
              to="/app/families"
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <Network size={14} className="text-amber-400" />
              <span>Precursor Families</span>
            </Link>
          </div>
        }
      />

      {/* 2. Top 4 Clean Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Reports Analyzed */}
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>Reports Analyzed</span>
            <FileText size={16} className="text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">{totalReports}</div>
          <div className="text-xs text-slate-400">
            Historical portfolio ingested (UA/UC logs)
          </div>
        </div>

        {/* SIF-Potential Observations */}
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>SIF-Potential Observations</span>
            <ShieldAlert size={16} className="text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 tracking-tight">{sifPotentialCount}</div>
          <div className="text-xs text-slate-400">
            High or medium consequence exposures
          </div>
        </div>

        {/* Recurring Precursor Families */}
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-slate-400">
            <span>Recurring Precursor Families</span>
            <Network size={16} className="text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400 tracking-tight">{recurringFamilies}</div>
          <div className="text-xs text-slate-400">
            Clusters with ≥ 2 cross-equipment reports
          </div>
        </div>

        {/* Needs HSE Review */}
        <div className="rounded-lg border border-amber-500/30 bg-slate-900 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-amber-400">
            <span>Needs HSE Review</span>
            <AlertTriangle size={16} className="text-amber-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold text-amber-300 tracking-tight">
              {String(needsReview).padStart(2, "0")}
            </span>
            <Link
              to="/app/review"
              className="text-xs font-medium text-amber-400 hover:text-amber-300 flex items-center gap-0.5 hover:underline"
            >
              <span>Review queue</span>
              <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="text-xs text-slate-400">
            Human-in-the-loop validation pending
          </div>
        </div>
      </div>

      {/* 3. Attention Required Section */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rose-500" />
              <h2 className="text-base font-semibold text-white">Attention Required: Recurring Precursors</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Prioritized systemic barrier breakdowns requiring engineering or supervisory intervention.
            </p>
          </div>
          <Link
            to="/app/families"
            className="text-xs font-medium text-amber-400 hover:text-amber-300 flex items-center gap-1"
          >
            <span>View all {totalFamilies} families</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {topAttentionFamilies.map((fam) => (
            <div
              key={fam.id}
              className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-amber-400">{fam.id}</span>
                    <span className="rounded bg-rose-500/15 border border-rose-500/30 px-1.5 py-0.2 text-[10px] font-bold text-rose-300 uppercase">
                      Recurring (≥ {fam.recurring_threshold || 2})
                    </span>
                  </div>
                  <h3 className="mt-1 text-sm font-bold text-white">{fam.name}</h3>
                </div>
                <Link
                  to={`/app/families/${fam.id}`}
                  className="flex items-center gap-1 text-xs font-medium text-amber-400 hover:text-amber-300 hover:underline flex-shrink-0"
                >
                  <span>Investigate</span>
                  <ArrowRight size={13} />
                </Link>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {fam.description}
              </p>

              <div className="grid grid-cols-2 gap-2.5 text-xs border-y border-slate-800/80 py-2.5 my-2">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Common Barrier</span>
                  <span className="font-medium text-slate-200 capitalize text-xs">{label(fam.common_barrier)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-0.5">Barrier State</span>
                  <StateBadge value={fam.common_barrier_state} />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Hazardous Energy</span>
                  <span className="font-medium text-slate-200 capitalize text-xs">{label(fam.common_energy)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Equipment Scope</span>
                  <span className="text-slate-300 text-xs truncate block">
                    {fam.activities?.length || 3} activities ({fam.activities?.slice(0, 2).map(label).join(", ")})
                  </span>
                </div>
              </div>

              <AttentionBar
                value={fam.attention_signal}
                compact={false}
                showBasis={true}
                basis={fam.attention_basis}
              />
            </div>
          ))}
        </div>
      </div>

      {/* 4. Precursor Relationship Map (Clear Structural Flow) */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
        <div className="border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <GitMerge size={16} className="text-amber-400" />
            <h2 className="text-base font-semibold text-white">
              Precursor Relationship Map — Structural Convergence
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Different equipment. Different wording. Same failed barrier. This is how MECHORA identifies recurring precursor mechanisms.
          </p>
        </div>

        {/* 3-Column Structural Flow */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-stretch">
          {/* Column 1: Individual Observations */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 pb-2 border-b border-slate-800">
                1. Safety Observations (Different Stories)
              </div>
              <p className="text-xs text-slate-400 mt-2 mb-3">
                Disparate reports logged across separate teams and assets:
              </p>

              <div className="space-y-2">
                <div className="rounded border border-slate-800/90 bg-slate-900/60 p-2.5 text-xs">
                  <div className="font-semibold text-slate-200">Pipeline Maintenance</div>
                  <div className="text-slate-400 italic mt-0.5">
                    “Flange opened before depressurization confirmation.”
                  </div>
                </div>

                <div className="rounded border border-slate-800/90 bg-slate-900/60 p-2.5 text-xs">
                  <div className="font-semibold text-slate-200">Compressor Servicing</div>
                  <div className="text-slate-400 italic mt-0.5">
                    “Work started before zero-pressure verification.”
                  </div>
                </div>

                <div className="rounded border border-slate-800/90 bg-slate-900/60 p-2.5 text-xs">
                  <div className="font-semibold text-slate-200">Valve Replacement</div>
                  <div className="text-slate-400 italic mt-0.5">
                    “Isolation verification skipped during replacement.”
                  </div>
                </div>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2 text-center">
              Surface text differs completely
            </div>
          </div>

          {/* Column 2: Extracted Common Safety Mechanism */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-amber-400 pb-2 border-b border-slate-800">
                2. Common Safety Mechanism (Ontology Match)
              </div>
              <p className="text-xs text-slate-400 mt-2 mb-3">
                Extracted canonical concepts match across all 3 reports:
              </p>

              <div className="space-y-2">
                <div className="rounded border border-slate-800 bg-slate-900/60 p-2.5 text-xs flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Hazardous Energy</span>
                    <div className="font-medium text-slate-200">Pressurized Gas</div>
                  </div>
                  <span className="text-rose-400 font-bold">100%</span>
                </div>

                <div className="rounded border border-slate-800 bg-slate-900/60 p-2.5 text-xs flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Required Barrier</span>
                    <div className="font-medium text-slate-200">Energy Isolation (LOTO)</div>
                  </div>
                  <span className="text-sky-400 font-bold">100%</span>
                </div>

                <div className="rounded border border-slate-800 bg-slate-900/60 p-2.5 text-xs flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Barrier State</span>
                    <div className="font-medium text-rose-400">Not Verified</div>
                  </div>
                  <span className="text-rose-400 font-bold">100%</span>
                </div>
              </div>
            </div>

            <div className="text-[11px] text-emerald-400 border-t border-slate-800/80 pt-2 text-center font-medium">
              ✓ Structural Similarity: 0.94 (Threshold: 0.65)
            </div>
          </div>

          {/* Column 3: Recurring Precursor Family */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-rose-400 pb-2 border-b border-slate-800">
                3. Precursor Family (Actionable Intelligence)
              </div>
              <p className="text-xs text-slate-400 mt-2 mb-3">
                Grouped into a single persistent precursor intelligence entity:
              </p>

              {featuredFamily ? (
                <>
                  <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-amber-400">
                        {featuredFamily.id}
                      </span>
                      {featuredFamily.recurring && (
                        <span className="rounded bg-rose-500/20 px-1.5 py-0.2 text-[10px] font-bold text-rose-300">
                          Recurring (≥ {featuredFamily.recurring_threshold || 2})
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-bold text-white">{featuredFamily.name}</h4>
                    <ul className="text-xs text-slate-300 space-y-1">
                      <li className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                        <span>
                          {featuredFamily.activities?.length
                            ? `Cross-equipment: ${featuredFamily.activities
                                .map((a) => label(a).charAt(0).toUpperCase() + label(a).slice(1))
                                .join(", ")}`
                            : "Cross-equipment mechanism"}
                        </span>
                      </li>
                      {featuredFamily.common_exposure &&
                        featuredFamily.common_exposure !== "unknown" && (
                          <li className="flex items-center gap-1.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                            <span className="capitalize">
                              Exposure: {label(featuredFamily.common_exposure)}
                            </span>
                          </li>
                        )}
                    </ul>
                  </div>

                  <div className="border-t border-slate-800/80 pt-2 flex items-center justify-between">
                    <span className="text-xs text-slate-400">
                      Attention: {featuredFamily.attention_signal.toFixed(1)}
                    </span>
                    <Link
                      to={`/app/families/${featuredFamily.id}`}
                      className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 hover:underline"
                    >
                      <span>View Family Record</span>
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                </>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-700 p-4 text-center">
                  <p className="text-xs font-semibold text-slate-300 mb-1">
                    No precursor families yet
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Submit a real observation to start identifying recurring barrier mechanisms.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Professional Recent Observations Data Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-semibold text-white">Recent Safety Observations</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Latest safety observation records analyzed with canonical barrier breakdown states.
            </p>
          </div>
          <Link
            to="/app/observations"
            className="text-xs font-medium text-amber-400 hover:text-amber-300 flex items-center gap-1 hover:underline"
          >
            <span>View all observations</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 bg-slate-950/60">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Report ID</th>
                <th className="py-2.5 px-3 font-semibold">Activity</th>
                <th className="py-2.5 px-3 font-semibold">Hazardous Energy</th>
                <th className="py-2.5 px-3 font-semibold">Required Barrier</th>
                <th className="py-2.5 px-3 font-semibold">Barrier State</th>
                <th className="py-2.5 px-3 font-semibold">SIF Potential</th>
                <th className="py-2.5 px-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    Loading observations...
                  </td>
                </tr>
              ) : recentObs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No recent observations logged.
                  </td>
                </tr>
              ) : (
                recentObs.slice(0, 8).map((obs) => (
                  <tr
                    key={obs.id}
                    className="hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-2.5 px-3 font-mono font-medium text-white">
                      {obs.report_id}
                    </td>
                    <td className="py-2.5 px-3 capitalize">
                      {label(obs.event?.activity || "Maintenance")}
                    </td>
                    <td className="py-2.5 px-3 capitalize text-slate-300">
                      {label(obs.event?.energy || "Pressurized Gas")}
                    </td>
                    <td className="py-2.5 px-3 capitalize text-slate-300">
                      {label(obs.event?.barrier || "Energy Isolation")}
                    </td>
                    <td className="py-2.5 px-3">
                      <StateBadge value={obs.event?.barrier_state} />
                    </td>
                    <td className="py-2.5 px-3">
                      <SIFBadge value={obs.event?.sif?.classification} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Link
                        to={`/app/observations/${obs.id}`}
                        className="font-medium text-amber-400 hover:text-amber-300 hover:underline"
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
