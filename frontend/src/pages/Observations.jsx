import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search,
  Filter,
  ArrowUpDown,
  FileText,
  Plus,
  ArrowRight,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { api, label } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge, ValidationBadge } from "../components/common/StatusBadge.jsx";

export default function Observations() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQ = searchParams.get("q") || "";

  const [observations, setObservations] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState("");

  const [query, setQuery] = useState(initialQ);
  const [stateFilter, setStateFilter] = useState("");
  const [sifFilter, setSifFilter] = useState("");
  const [activityFilter, setActivityFilter] = useState("");
  const [sortBy, setSortBy] = useState("newest");

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.observations({
        q: query || undefined,
        barrier_state: stateFilter || undefined,
        sif: sifFilter || undefined,
        activity: activityFilter || undefined,
        limit: 100,
      });

      let list = res.observations || [];

      // Sort client-side
      if (sortBy === "newest") {
        list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      } else if (sortBy === "oldest") {
        list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      } else if (sortBy === "sif") {
        const order = { high: 4, medium: 3, low: 2, needs_review: 1 };
        list.sort(
          (a, b) =>
            (order[b.event?.sif?.classification] || 0) -
            (order[a.event?.sif?.classification] || 0),
        );
      } else if (sortBy === "confidence") {
        list.sort((a, b) => (b.event?.confidence || 0) - (a.event?.confidence || 0));
      }

      setObservations(list);
      setTotal(res.total ?? list.length);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [stateFilter, sifFilter, activityFilter, sortBy]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadData();
  };

  const handleResetFilters = () => {
    setStateFilter("");
    setSifFilter("");
    setActivityFilter("");
    setQuery("");
    setSortBy("newest");
  };

  const handleDelete = async (obs) => {
    if (
      !window.confirm(
        `Delete observation "${obs.report_id}"?\n\nThis permanently removes the record and rebuilds precursor families. This cannot be undone.`,
      )
    ) {
      return;
    }
    setDeletingId(obs.id);
    try {
      await api.deleteObservation(obs.id);
    } finally {
      setDeletingId("");
    }
    loadData();
  };

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        title="Safety Observations"
        description="Browser for individual safety reports, structured safety events, grounded evidence spans, and validation status."
        badge={
          <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-mono font-semibold text-slate-300">
            {total} reports
          </span>
        }
        actions={
          <Link
            to="/app/analyze"
            className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-500 transition-colors shadow-sm"
          >
            <Plus size={14} />
            <span>Analyze New Observation</span>
          </Link>
        }
      />

      {/* 2. Compact Search & Filter Bar */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search narrative text, report ID, activity, or barrier..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-20 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
            />
            <button
              type="submit"
              className="absolute right-1.5 top-1.5 rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors"
            >
              Search
            </button>
          </form>

          {/* Sort Select */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <ArrowUpDown size={13} />
              <span>Sort:</span>
            </span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-2 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="sif">SIF Potential (High to Low)</option>
              <option value="confidence">Extraction Confidence</option>
            </select>
          </div>
        </div>

        {/* Filter Row */}
        <div className="flex flex-wrap items-center gap-2.5 pt-2 border-t border-slate-800 text-xs">
          <div className="flex items-center gap-1 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
            <Filter size={12} />
            <span>Filters:</span>
          </div>

          {/* Barrier State */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All Barrier States</option>
            <option value="not_verified">Not Verified</option>
            <option value="verified">Verified (Compliance)</option>
            <option value="failed">Failed</option>
            <option value="absent">Absent</option>
            <option value="partially_effective">Partially Effective</option>
            <option value="unknown">Unknown</option>
          </select>

          {/* SIF Status */}
          <select
            value={sifFilter}
            onChange={(e) => setSifFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All SIF Classifications</option>
            <option value="high">High SIF Potential</option>
            <option value="medium">Medium SIF Potential</option>
            <option value="low">Low SIF Potential</option>
            <option value="needs_review">Needs Review</option>
          </select>

          {/* Activity */}
          <select
            value={activityFilter}
            onChange={(e) => setActivityFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All Activities</option>
            <option value="pipeline_maintenance">Pipeline Maintenance</option>
            <option value="compressor_maintenance">Compressor Maintenance</option>
            <option value="valve_replacement">Valve Replacement</option>
            <option value="pump_maintenance">Pump Maintenance</option>
            <option value="hot_work">Hot Work</option>
            <option value="working_at_height">Working at Height</option>
          </select>

          {(stateFilter || sifFilter || activityFilter || query) && (
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
      </div>

      {/* 3. Observations Enterprise Data Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 bg-slate-950">
              <tr>
                <th className="py-3 px-3.5 font-semibold">Observation</th>
                <th className="py-3 px-3.5 font-semibold">Activity</th>
                <th className="py-3 px-3.5 font-semibold">Hazard / Energy</th>
                <th className="py-3 px-3.5 font-semibold">Barrier State</th>
                <th className="py-3 px-3.5 font-semibold">SIF Potential</th>
                <th className="py-3 px-3.5 font-semibold">Precursor Family</th>
                <th className="py-3 px-3.5 font-semibold">Review Status</th>
                <th className="py-3 px-3.5 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 text-xs">
                    Loading safety observations…
                  </td>
                </tr>
              ) : observations.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 text-xs">
                    <FileText size={24} className="mx-auto text-slate-600 mb-2" />
                    <div className="font-semibold text-slate-300">No Observations Found</div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      Try adjusting your search terms or filter criteria.
                    </div>
                  </td>
                </tr>
              ) : (
                observations.map((obs) => {
                  const event = obs.event || {};
                  return (
                    <tr
                      key={obs.id}
                      className="hover:bg-slate-800/40 transition-colors group"
                    >
                      {/* Observation ID & snippet */}
                      <td className="py-3 px-3.5">
                        <Link
                          to={`/app/observations/${obs.id}`}
                          className="font-mono text-xs font-bold text-white hover:text-amber-400 transition-colors block"
                        >
                          {obs.report_id}
                        </Link>
                        <span className="font-mono text-[10px] text-slate-500 block truncate max-w-[130px]">
                          {obs.id}
                        </span>
                      </td>

                      {/* Activity */}
                      <td className="py-3 px-3.5 font-medium text-slate-200 capitalize whitespace-nowrap">
                        {label(event.activity || "Maintenance")}
                      </td>

                      {/* Hazard / Energy */}
                      <td className="py-3 px-3.5 text-slate-300 capitalize whitespace-nowrap">
                        {label(event.energy || "Pressurized Gas")}
                      </td>

                      {/* Barrier State */}
                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <StateBadge value={event.barrier_state} />
                      </td>

                      {/* SIF Potential */}
                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <SIFBadge value={event.sif?.classification} />
                      </td>

                      {/* Precursor Family */}
                      <td className="py-3 px-3.5 whitespace-nowrap">
                        {obs.precursor_family_id ? (
                          <Link
                            to={`/app/families/${obs.precursor_family_id}`}
                            className="font-mono text-xs font-semibold text-sky-400 hover:text-sky-300 hover:underline"
                          >
                            {obs.precursor_family_id}
                          </Link>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Unassigned</span>
                        )}
                      </td>

                      {/* Review Status */}
                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <ValidationBadge status={obs.validation} />
                      </td>

                      {/* Action Link */}
                      <td className="py-3 px-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2.5">
                          <Link
                            to={`/app/observations/${obs.id}`}
                            className="font-medium text-amber-400 hover:text-amber-300 flex items-center gap-1 hover:underline"
                          >
                            <span>Details</span>
                            <ArrowRight size={12} />
                          </Link>
                          <button
                            type="button"
                            title="Delete observation"
                            disabled={deletingId === obs.id}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleDelete(obs);
                            }}
                            className="text-slate-500 hover:text-rose-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer */}
        <div className="border-t border-slate-800 bg-slate-950 px-4 py-2.5 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {observations.length} observations</span>
          <span className="italic text-[11px] text-slate-500">
            Click any row or ID to inspect full evidence spans and canonical extraction
          </span>
        </div>
      </div>
    </div>
  );
}
