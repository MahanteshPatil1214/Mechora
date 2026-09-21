import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Network,
  Filter,
  ArrowRight,
  GitMerge,
  RotateCcw,
  Shield,
  Layers,
} from "lucide-react";
import { api, label, summarizeCapaForBarrier } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge } from "../components/common/StatusBadge.jsx";
import { AttentionBar } from "../components/common/AttentionBar.jsx";
import { CapaInsightStrip } from "../components/CapaEffectiveness.jsx";

export default function PrecursorFamilies() {
  const [families, setFamilies] = useState([]);
  const [capas, setCapas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recOnly, setRecOnly] = useState(false);
  const [barrierFilter, setBarrierFilter] = useState("");
  const [energyFilter, setEnergyFilter] = useState("");

  useEffect(() => {
    api
      .capas({ limit: 500 })
      .then((res) => setCapas(res.capas || []))
      .catch(() => {});
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.families(recOnly);
      let list = res.families || [];

      if (barrierFilter) {
        list = list.filter((f) => f.common_barrier === barrierFilter);
      }
      if (energyFilter) {
        list = list.filter((f) => f.common_energy === energyFilter);
      }

      // Sort by attention signal desc
      list.sort((a, b) => (b.attention_signal || 0) - (a.attention_signal || 0));

      setFamilies(list);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [recOnly, barrierFilter, energyFilter]);

  const handleResetFilters = () => {
    setBarrierFilter("");
    setEnergyFilter("");
    setRecOnly(false);
  };

  const recurringCount = families.filter((f) => f.recurring).length;
  const patternBadge = recOnly
    ? `${families.length} recurring pattern${families.length === 1 ? "" : "s"}`
    : families.length > 0
      ? `${families.length} pattern${families.length === 1 ? "" : "s"} · ${recurringCount} recurring · ${families.length - recurringCount} emerging`
      : "No patterns";

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Page Header */}
      <PageHeader
        title="Precursor Patterns"
        description="Catalog of structural safety mechanisms identified across disparate reporting phrasing, locations, and equipment types."
        badge={
          <span className="rounded bg-slate-800 px-2.5 py-0.5 text-xs font-mono font-semibold text-slate-300">
            {patternBadge}
          </span>
        }
        actions={
          <label className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 cursor-pointer hover:border-slate-700 transition-colors">
            <input
              type="checkbox"
              checked={recOnly}
              onChange={(e) => setRecOnly(e.target.checked)}
              className="accent-amber-500 rounded"
            />
            <span>Recurring Only (≥ 2 reports)</span>
          </label>
        }
      />

      {/* 2. Conceptual Mechanism Banner */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 uppercase tracking-wider">
            <GitMerge size={15} />
            <span>Structural Precursor Principle:</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <span className="rounded bg-slate-950 px-2.5 py-1 text-slate-300 border border-slate-800">
              Different Safety Stories
            </span>
            <span className="text-amber-400 font-bold">→</span>
            <span className="rounded bg-slate-950 px-2.5 py-1 text-slate-300 border border-slate-800">
              Same Safety Mechanism
            </span>
            <span className="text-amber-400 font-bold">→</span>
            <span className="rounded bg-rose-500/15 px-2.5 py-1 text-rose-300 border border-rose-500/30 font-bold">
              Recurring Precursor Family
            </span>
          </div>
        </div>
      </div>

      {/* 3. Compact Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5 rounded-lg border border-slate-800 bg-slate-900 p-3 text-xs">
        <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
          <Filter size={12} />
          <span>Filters:</span>
        </div>

        <select
          value={barrierFilter}
          onChange={(e) => setBarrierFilter(e.target.value)}
          className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
        >
          <option value="">All Common Barriers</option>
          <option value="energy_isolation">Energy Isolation</option>
          <option value="hot_work_controls">Hot Work Controls</option>
          <option value="fall_protection">Fall Protection</option>
          <option value="confined_space_procedure">Confined Space Procedure</option>
          <option value="machinery_guarding">Machinery Guarding</option>
        </select>

        <select
          value={energyFilter}
          onChange={(e) => setEnergyFilter(e.target.value)}
          className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
        >
          <option value="">All Hazardous Energies</option>
          <option value="pressurized_gas">Pressurized Gas</option>
          <option value="flammable_atmosphere">Flammable Atmosphere</option>
          <option value="electrical_energy">Electrical Energy</option>
          <option value="gravity">Gravity / Fall from Height</option>
          <option value="moving_equipment">Moving Equipment</option>
        </select>

        {(barrierFilter || energyFilter || recOnly) && (
          <button
            type="button"
            onClick={handleResetFilters}
            className="text-amber-400 hover:text-amber-300 font-medium text-xs underline ml-auto flex items-center gap-1"
          >
            <RotateCcw size={11} />
            <span>Reset Filters</span>
          </button>
        )}
      </div>

      {/* 4. Family Cards Grid */}
      {loading ? (
        <div className="py-16 text-center text-xs text-slate-500">
          Loading precursor families…
        </div>
      ) : families.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-12 text-center space-y-3">
          <Network size={32} className="mx-auto text-slate-600" />
          <h3 className="text-sm font-bold text-white">No Precursor Families Match</h3>
          <p className="text-xs text-slate-400">Try relaxing your filter parameters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {families.map((fam) => {
            const obsCount = fam.observation_ids?.length || 0;
            const activities = fam.activities || [];

            return (
              <div
                key={fam.id}
                className="flex flex-col justify-between rounded-lg border border-slate-800 bg-slate-900 p-5 hover:border-slate-700 transition-colors space-y-4 group"
              >
                <div className="space-y-3">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-amber-400">
                          {fam.id}
                        </span>
                        {fam.recurring && (
                          <span className="rounded bg-rose-500/15 border border-rose-500/30 px-1.5 py-0.2 text-[10px] font-bold text-rose-300 uppercase tracking-wider">
                            Recurring (≥ {fam.recurring_threshold || 2})
                          </span>
                        )}
                      </div>
                      <h3 className="mt-1 text-base font-bold text-white group-hover:text-amber-400 transition-colors">
                        {fam.name}
                      </h3>
                    </div>
                    <span className="rounded bg-slate-950 border border-slate-800 px-2.5 py-1 font-mono text-xs font-bold text-slate-300 flex-shrink-0">
                      {obsCount} reports
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                    {fam.description}
                  </p>

                  {/* Core Mechanism 4-Field Row */}
                  <div className="grid grid-cols-2 gap-2 text-xs rounded border border-slate-800/80 bg-slate-950 p-2.5">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">
                        Common Barrier:
                      </span>
                      <span className="font-medium text-slate-200 capitalize truncate block">
                        {label(fam.common_barrier)}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">
                        Barrier State:
                      </span>
                      <StateBadge value={fam.common_barrier_state} />
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">
                        Hazard / Energy:
                      </span>
                      <span className="font-medium text-slate-200 capitalize truncate block">
                        {label(fam.common_energy)}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 block">
                        Exposure Consequence:
                      </span>
                      <span className="font-medium text-slate-200 capitalize truncate block">
                        {label(fam.common_exposure)}
                      </span>
                    </div>
                  </div>

                  {/* Distinct Activities Spread */}
                  {activities.length > 0 && (
                    <div className="text-xs space-y-1">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                        Equipment / Activity Convergence ({activities.length}):
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {activities.map((act) => (
                          <span
                            key={act}
                            className="rounded border border-slate-800 bg-slate-950 px-2 py-0.5 text-[11px] text-slate-300 capitalize"
                          >
                            {label(act)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Attention Signal Bar */}
                  <div className="pt-2 border-t border-slate-800">
                    <AttentionBar
                      value={fam.attention_signal}
                      compact={true}
                    />
                  </div>

                  {/* CAPA / Effectiveness signal for this barrier */}
                  <CapaInsightStrip
                    barrier={fam.common_barrier}
                    summary={summarizeCapaForBarrier(capas, fam.common_barrier)}
                  />
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    {fam.exclusions?.length || 0} structurally separated exclusion(s)
                  </span>
                  <Link
                    to={`/app/families/${fam.id}`}
                    className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:underline"
                  >
                    <span>Investigate Family Record</span>
                    <ArrowRight size={13} />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
