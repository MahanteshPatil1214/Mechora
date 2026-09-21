import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  ArrowRight,
  Trash2,
  CheckCircle2,
  X,
  ClipboardCheck,
  BarChart3,
  ShieldAlert,
} from "lucide-react";
import {
  api,
  label,
  capaStatusLabel,
  effectivenessStatusLabel,
  capaEvaluationPeriod,
  EFFECTIVENESS_STYLES,
  CAPA_STATUS_STYLES,
} from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";

const BARRIER_OPTIONS = [
  "energy_isolation",
  "hot_work_controls",
  "machinery_guarding",
  "confined_space_procedure",
  "working_at_height",
  "line_of_fire",
  "safe_chemical_handling",
];

const emptyDraft = {
  title: "",
  description: "",
  linked_barrier_id: "energy_isolation",
  location: "",
  site: "",
  status: "open",
  window_days: 90,
};

export default function Capas() {
  const [capas, setCapas] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [barrierFilter, setBarrierFilter] = useState("");
  const [deletingId, setDeletingId] = useState("");
  const [closingId, setClosingId] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState(emptyDraft);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.capas({
        status: statusFilter || undefined,
        linkedBarrierId: barrierFilter || undefined,
        limit: 100,
        offset: 0,
      });
      setCapas(res.capas || []);
      setTotal(res.total ?? (res.capas || []).length);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, barrierFilter]);

  const flash = (msg) => {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(""), 4000);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!draft.title.trim()) return;
    setCreating(true);
    try {
      const created = await api.createCapa({
        title: draft.title,
        description: draft.description,
        linked_barrier_id: draft.linked_barrier_id,
        location: draft.location,
        site: draft.site,
        status: draft.status,
        window_days: Number(draft.window_days) || 90,
      });
      setShowCreate(false);
      setDraft(emptyDraft);
      flash(`CAPA "${created.report_id}" created. Effectiveness: ${effectivenessStatusLabel(created.effectiveness_status)}.`);
      loadData();
    } catch (err) {
      flash(`Failed to create CAPA: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  const handleClose = async (capa) => {
    if (
      !window.confirm(
        `Close CAPA "${capa.report_id}"?\n\nClosing freezes the post-closure evidence window and recomputes effectiveness deterministically.`,
      )
    ) {
      return;
    }
    setClosingId(capa.id);
    try {
      const updated = await api.updateCapaStatus(
        capa.id,
        "closed",
        new Date().toISOString(),
      );
      flash(
        `CAPA "${capa.report_id}" closed. Effectiveness verdict: ${effectivenessStatusLabel(updated.effectiveness_status)}.`,
      );
      loadData();
    } catch (err) {
      flash(`Failed to close CAPA: ${err.message}`);
    } finally {
      setClosingId("");
    }
  };

  const handleDelete = async (capa) => {
    if (
      !window.confirm(
        `Delete CAPA "${capa.report_id}"?\n\nThis permanently removes the CAPA record. This cannot be undone.`,
      )
    ) {
      return;
    }
    setDeletingId(capa.id);
    try {
      await api.deleteCapa(capa.id);
      flash(`CAPA "${capa.report_id}" deleted.`);
      loadData();
    } catch (err) {
      flash(`Failed to delete CAPA: ${err.message}`);
    } finally {
      setDeletingId("");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Corrective & Preventive Actions"
        description="CAPAs targeted at barrier failures, with deterministic evidence-based effectiveness verdicts: baseline evidence before creation vs recurrence evidence after closure."
        badge={
          <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-mono font-semibold text-slate-300">
            {total} CAPAs
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-500 transition-colors shadow-sm"
          >
            <Plus size={14} />
            <span>New CAPA</span>
          </button>
        }
      />

      {actionMsg && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {showCreate && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <ClipboardCheck size={15} className="text-amber-400" />
              <span>Create CAPA</span>
            </h2>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="text-slate-500 hover:text-slate-300"
              aria-label="Close create form"
            >
              <X size={16} />
            </button>
          </div>

          <form onSubmit={handleCreate} className="space-y-3">
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  minLength={4}
                  maxLength={160}
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  placeholder="e.g. Introduce mandatory isolation verification checklist."
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                Description
              </label>
              <textarea
                value={draft.description}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                rows={2}
                maxLength={4000}
                placeholder="What is being corrected / prevented, and which barrier does it target?"
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Linked Barrier *
                </label>
                <select
                  value={draft.linked_barrier_id}
                  onChange={(e) =>
                    setDraft({ ...draft, linked_barrier_id: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
                >
                  {BARRIER_OPTIONS.map((b) => (
                    <option key={b} value={b}>
                      {label(b)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Location
                </label>
                <input
                  type="text"
                  maxLength={80}
                  value={draft.location}
                  onChange={(e) => setDraft({ ...draft, location: e.target.value })}
                  placeholder="e.g. process_area"
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Site
                </label>
                <input
                  type="text"
                  maxLength={80}
                  value={draft.site}
                  onChange={(e) => setDraft({ ...draft, site: e.target.value })}
                  placeholder="e.g. EAST"
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1">
                  Baseline Window (days)
                </label>
                <input
                  type="number"
                  min={7}
                  max={365}
                  value={draft.window_days}
                  onChange={(e) => setDraft({ ...draft, window_days: e.target.value })}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="rounded-lg border border-slate-800 px-3.5 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-amber-500 disabled:opacity-40 transition-colors"
              >
                <Plus size={14} />
                <span>{creating ? "Creating…" : "Create CAPA"}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          <span className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
            Filters:
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="closed">Closed</option>
            <option value="cancelled">Cancelled</option>
            <option value="draft">Draft</option>
          </select>
          <select
            value={barrierFilter}
            onChange={(e) => setBarrierFilter(e.target.value)}
            className="rounded border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs text-slate-300 focus:border-amber-500 focus:outline-none"
          >
            <option value="">All Barriers</option>
            {BARRIER_OPTIONS.map((b) => (
              <option key={b} value={b}>
                {label(b)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 bg-slate-950">
              <tr>
                <th className="py-3 px-3.5 font-semibold">CAPA</th>
                <th className="py-3 px-3.5 font-semibold">Linked Barrier</th>
                <th className="py-3 px-3.5 font-semibold">Status</th>
                <th className="py-3 px-3.5 font-semibold">Effectiveness</th>
                <th className="py-3 px-3.5 font-semibold">Baseline</th>
                <th className="py-3 px-3.5 font-semibold">Affected Sites</th>
                <th className="py-3 px-3.5 font-semibold">Post-CAPA</th>
                <th className="py-3 px-3.5 font-semibold">Created</th>
                <th className="py-3 px-3.5 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500 text-xs">
                    Loading CAPAs…
                  </td>
                </tr>
              ) : capas.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400 text-xs">
                    <ClipboardCheck size={24} className="mx-auto text-slate-600 mb-2" />
                    <div className="font-semibold text-slate-300">No CAPAs Found</div>
                    <div className="text-slate-500 text-[11px] mt-0.5">
                      Create a CAPA targeting a barrier failure to begin effectiveness tracking.
                    </div>
                  </td>
                </tr>
              ) : (
                capas.map((capa) => {
                  const effCls =
                    EFFECTIVENESS_STYLES[capa.effectiveness_status] ||
                    EFFECTIVENESS_STYLES.insufficient_evidence;
                  const stCls = CAPA_STATUS_STYLES[capa.status] || CAPA_STATUS_STYLES.open;
                  const baselineFailures = capa.baseline?.failure_count ?? 0;
                  const recurrences = capa.post_capa?.recurrence_count ?? 0;
                  const postObs = (capa.post_capa?.observation_ids || []).length;
                  const evalPeriod = capaEvaluationPeriod(capa);
                  const baselineDays = evalPeriod.baselineDays;
                  return (
                    <tr
                      key={capa.id}
                      className="hover:bg-slate-800/40 transition-colors group"
                    >
                      <td className="py-3 px-3.5">
                        <Link
                          to={`/app/capas/${capa.id}`}
                          className="font-mono text-xs font-bold text-white hover:text-amber-400 transition-colors block"
                        >
                          {capa.report_id}
                        </Link>
                        <span className="text-[10px] text-slate-500 block truncate max-w-[180px]">
                          {capa.title}
                        </span>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap lower-case">
                        <span className="rounded border border-slate-700 bg-slate-800/50 px-2 py-0.5 text-[11px] font-semibold text-slate-300 capitalize">
                          {label(capa.linked_barrier_id)}
                        </span>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${stCls}`}
                        >
                          {capaStatusLabel(capa.status)}
                        </span>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${effCls}`}
                        >
                          {effectivenessStatusLabel(capa.effectiveness_status)}
                        </span>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-mono text-xs font-bold ${
                              baselineFailures > 0 ? "text-rose-400" : "text-slate-500"
                            }`}
                          >
                            {baselineFailures} fail
                          </span>
                          <span className="text-slate-600">·</span>
                          <span className="font-mono text-[11px] text-slate-400">
                            {(capa.baseline?.observation_ids || []).length} obs
                          </span>
                        </div>
                        <div className="font-mono text-[10px] text-slate-500 mt-0.5">
                          {baselineDays}d window
                        </div>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <span className="font-mono text-xs font-bold text-slate-200">
                          {capa.baseline?.affected_sites ?? 0}
                        </span>
                        <div className="text-[10px] text-slate-500 mt-0.5">sites</div>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-mono text-xs font-bold ${
                              recurrences > 0 ? "text-rose-400" : "text-emerald-400"
                            }`}
                          >
                            {recurrences} recurr
                          </span>
                          <span className="text-slate-600">·</span>
                          <span className="font-mono text-[11px] text-slate-400">
                            {postObs} obs
                          </span>
                        </div>
                        <div className="font-mono text-[10px] text-slate-500 mt-0.5">
                          {evalPeriod.postOpen ? `${evalPeriod.postElapsed}d elapsed` : "not opened"}
                        </div>
                      </td>

                      <td className="py-3 px-3.5 whitespace-nowrap text-slate-400">
                        {new Date(capa.created_at).toLocaleDateString()}
                      </td>

                      <td className="py-3 px-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2.5">
                          {capa.status === "open" || capa.status === "in_progress" ? (
                            <button
                              type="button"
                              disabled={closingId === capa.id}
                              onClick={() => handleClose(capa)}
                              title="Close CAPA and recompute effectiveness"
                              className="flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[11px] font-bold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 transition-colors"
                            >
                              <CheckCircle2 size={12} />
                              <span>{closingId === capa.id ? "Closing…" : "Close"}</span>
                            </button>
                          ) : null}
                          <Link
                            to={`/app/capas/${capa.id}`}
                            className="font-medium text-amber-400 hover:text-amber-300 flex items-center gap-1 hover:underline"
                          >
                            <span>Details</span>
                            <ArrowRight size={12} />
                          </Link>
                          <button
                            type="button"
                            title="Delete CAPA"
                            disabled={deletingId === capa.id}
                            onClick={() => handleDelete(capa)}
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

        <div className="border-t border-slate-800 bg-slate-950 px-4 py-2.5 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {capas.length} CAPAs</span>
          <span className="italic text-[11px] text-slate-500 flex items-center gap-1.5">
            <ShieldAlert size={12} />
            Effectiveness is derived from persisted barrier-state evidence — never fabricated scores
          </span>
        </div>
      </div>
    </div>
  );
}