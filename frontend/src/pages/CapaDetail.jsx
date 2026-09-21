import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  TrendingDown,
  RotateCcw,
  FileQuestion,
  Eye,
  ExternalLink,
  Trash2,
  CalendarClock,
  MapPin,
  Building2,
  ShieldAlert,
  ListChecks,
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

const EFF_ICONS = {
  improvement_observed: TrendingDown,
  recurrence_detected: RotateCcw,
  insufficient_evidence: FileQuestion,
  under_observation: Eye,
};

export default function CapaDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [capa, setCapa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [closing, setClosing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [actionMsg, setActionMsg] = useState("");
  const [error, setError] = useState("");
  const [showWhy, setShowWhy] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .capa(id)
      .then(setCapa)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const flash = (msg) => {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(""), 5000);
  };

  const handleClose = async () => {
    if (
      !window.confirm(
        `Close CAPA "${capa.report_id}"?\n\nClosing freezes the post-closure evidence window and recomputes effectiveness deterministically.`,
      )
    ) {
      return;
    }
    setClosing(true);
    try {
      const updated = await api.updateCapaStatus(
        capa.id,
        "closed",
        new Date().toISOString(),
      );
      setCapa(updated);
      flash(
        `CAPA closed. Effectiveness verdict: ${effectivenessStatusLabel(updated.effectiveness_status)}.`,
      );
    } catch (err) {
      flash(`Failed to close CAPA: ${err.message}`);
    } finally {
      setClosing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete CAPA "${capa.report_id}"? This cannot be undone.`)) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteCapa(capa.id);
      navigate("/app/capas", {
        state: { deleted: capa.report_id, _t: Date.now() },
      });
    } catch (err) {
      flash(`Failed to delete CAPA: ${err.message}`);
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-16 text-center text-xs text-slate-500">
        Loading CAPA details…
      </div>
    );
  }

  if (error || !capa) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-12 text-center space-y-4">
        <ClipboardCheck size={28} className="mx-auto text-slate-600" />
        <h2 className="text-base font-bold text-white">CAPA Record Not Found</h2>
        <p className="text-xs text-slate-400">{error || "The requested CAPA ID could not be located."}</p>
        <Link
          to="/app/capas"
          className="inline-block rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-amber-500 transition-colors"
        >
          ← Return to CAPAs
        </Link>
      </div>
    );
  }

  const baseline = capa.baseline || {};
  const post = capa.post_capa || {};
  const basis = capa.effectiveness_basis || {};
  const effCls =
    EFFECTIVENESS_STYLES[capa.effectiveness_status] ||
    EFFECTIVENESS_STYLES.insufficient_evidence;
  const stCls = CAPA_STATUS_STYLES[capa.status] || CAPA_STATUS_STYLES.open;
  const EffIcon = EFF_ICONS[capa.effectiveness_status] || Eye;
  const isOpen = capa.status === "open" || capa.status === "in_progress";
  const evalPeriod = capaEvaluationPeriod(capa);

  const evidenceIds = [
    ...(baseline.observation_ids || []),
    ...(post.observation_ids || []),
  ];
  const uniqueEvidence = [...new Set(evidenceIds)];
  const recurrenceIds = post.recurrence_observation_ids || [];

  const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");
  const fmtWindow = (from, to) =>
    from && to
      ? `${new Date(from).toLocaleDateString()} → ${new Date(to).toLocaleDateString()}`
      : "Not yet opened";
  const nowIso = new Date().toISOString();

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <PageHeader
        breadcrumb={
          <Link
            to="/app/capas"
            className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft size={13} />
            <span>Back to CAPAs</span>
          </Link>
        }
        title={capa.report_id}
        description={`${capa.title} · Linked barrier: ${label(capa.linked_barrier_id)}`}
        actions={
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${stCls}`}
            >
              {capaStatusLabel(capa.status)}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${effCls}`}
            >
              <EffIcon size={12} />
              <span>{effectivenessStatusLabel(capa.effectiveness_status)}</span>
            </span>
          </div>
        }
      />

      {actionMsg && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {/* Description + metadata */}
      {capa.description && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <p className="text-sm text-slate-300 leading-relaxed">{capa.description}</p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-3.5 flex items-center gap-3">
          <CalendarClock size={16} className="text-amber-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Created
            </div>
            <div className="text-xs text-slate-200 font-mono mt-0.5 truncate">
              {fmtDate(capa.created_at)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-3.5 flex items-center gap-3">
          <CheckCircle2 size={16} className="text-slate-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Closed
            </div>
            <div className="text-xs text-slate-200 font-mono mt-0.5 truncate">
              {fmtDate(capa.closed_at)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-3.5 flex items-center gap-3">
          <MapPin size={16} className="text-slate-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Location
            </div>
            <div className="text-xs text-slate-200 capitalize mt-0.5 truncate">
              {label(capa.location)}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-3.5 flex items-center gap-3">
          <Building2 size={16} className="text-slate-400 flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Site
            </div>
            <div className="text-xs text-slate-200 font-mono mt-0.5 truncate">
              {capa.site || "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Effectiveness verdict + basis */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-3">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
              Evidence-Based Effectiveness Verdict
            </span>
            <div
              className={`mt-1.5 inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-sm font-bold uppercase tracking-wider ${effCls}`}
            >
              <EffIcon size={15} />
              {effectivenessStatusLabel(capa.effectiveness_status)}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <button
              type="button"
              onClick={() => setShowWhy((v) => !v)}
              className={`flex items-center gap-1.5 rounded border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                showWhy
                  ? "border-amber-500/50 bg-amber-500/10 text-amber-300"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-amber-500/40 hover:text-amber-300"
              }`}
            >
              <ListChecks size={13} />
              <span>{showWhy ? "Hide evidence" : "Why? · Evidence"}</span>
            </button>
            <span className="text-[11px] text-slate-500 italic max-w-xs text-right">
              {basis.status_rule || "Derived from persisted barrier-state evidence."}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Baseline failures
            </div>
            <div className={`mt-1 font-mono text-xl font-black ${
              (baseline.failure_count || 0) > 0 ? "text-rose-400" : "text-slate-500"
            }`}>
              {baseline.failure_count ?? 0}
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              SIF potential baseline
            </div>
            <div className={`mt-1 font-mono text-xl font-black ${
              (baseline.sif_potential_count || 0) > 0 ? "text-amber-400" : "text-slate-500"
            }`}>
              {baseline.sif_potential_count ?? 0}
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">
              Post-CAPA recurrences
            </div>
            <div className={`mt-1 font-mono text-xl font-black ${
              (post.recurrence_count || 0) > 0 ? "text-rose-400" : "text-emerald-400"
            }`}>
              {post.recurrence_count ?? 0}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
          <span className="font-semibold uppercase tracking-wider text-slate-500">
            Evaluation period:
          </span>
          <span className="font-mono text-slate-200">
            Baseline: {evalPeriod.baselineDays} days
            <span className="text-slate-600"> | </span>
            {evalPeriod.postOpen
              ? `Post-CAPA: ${evalPeriod.postElapsed} days`
              : "Post-CAPA: not opened"}
          </span>
        </div>

        {showWhy && (
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-2.5">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                Evidence Chain
              </span>
              <span className="font-mono text-[10px] text-slate-500">
                Observation → Barrier Failure → CAPA → Closure → Subsequent Evidence → Verdict
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-1.5 text-xs text-slate-300">
              <div>
                Baseline failures:{" "}
                <span className="font-mono font-bold">{baseline.failure_count ?? 0}</span>
              </div>
              <div>
                Post-CAPA recurrences:{" "}
                <span className="font-mono font-bold">{post.recurrence_count ?? 0}</span>
              </div>
              <div>
                Affected sites:{" "}
                <span className="font-mono font-bold">{baseline.affected_sites ?? 0}</span>
              </div>
              <div>
                CAPA closure date:{" "}
                <span className="font-mono font-bold">{fmtDate(capa.closed_at)}</span>
              </div>
              <div className="sm:col-span-2">
                Baseline period:{" "}
                <span className="font-mono">
                  {fmtDate(baseline.from_iso)} → {fmtDate(baseline.to_iso)} ({evalPeriod.baselineDays} days)
                </span>
              </div>
              <div className="sm:col-span-2">
                {isOpen ? (
                  <span>Post window: not opened yet (opens at closure)</span>
                ) : (
                  <>
                    Post-CAPA evidence window:{" "}
                    <span className="font-mono">
                      {fmtWindow(post.from_iso, nowIso)} ({evalPeriod.postElapsed} days)
                    </span>{" "}
                    · configured maximum {evalPeriod.postDays} days
                  </>
                )}
              </div>
            </div>

            {uniqueEvidence.length > 0 && (
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1.5">
                  Supporting observation IDs ({uniqueEvidence.length}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {uniqueEvidence.map((oid) => (
                    <Link
                      key={oid}
                      to={`/app/observations/${oid}`}
                      className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
                    >
                      {oid}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            <p className="text-[10px] italic text-slate-500 border-t border-slate-800/70 pt-2">
              This is the evidence chain behind the verdict — shown as evidence, not causal proof that the CAPA worked.
            </p>
          </div>
        )}

        <p className="text-[11px] italic text-slate-500">
          {basis.derivation || basis.status_rule ||
            "Effectiveness is derived deterministically from persisted barrier-state observations in the baseline (pre-creation) and post-closure windows. Decision support only; not accident prediction."}
        </p>
      </div>

      {/* Baseline vs Post-CAPA evidence windows */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <ShieldAlert size={15} className="text-amber-400" />
              <span>Baseline Evidence (Before CAPA)</span>
            </h2>
            <span className="font-mono text-[11px] text-slate-500">
              window {baseline.window_days ?? 90}d
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Evidence window</span>
              <span className="font-mono text-slate-300">
                {fmtWindow(baseline.from_iso, baseline.to_iso)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Barrier state</span>
              <span className="capitalize text-slate-200 font-medium">
                {label(baseline.barrier_state)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Affected sites</span>
              <span className="font-mono text-slate-300">{baseline.affected_sites ?? 0}</span>
            </div>
          </div>

          {(baseline.observation_ids || []).length > 0 ? (
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Baseline Observations ({baseline.observation_ids.length}):
              </span>
              {baseline.observation_ids.map((oid) => (
                <Link
                  key={oid}
                  to={`/app/observations/${oid}`}
                  className="flex items-center justify-between rounded border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-300 hover:border-amber-500/40 hover:text-amber-300 transition-colors"
                >
                  <span className="font-mono font-semibold">{oid}</span>
                  <ExternalLink size={11} className="text-slate-500" />
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-[11px] italic text-slate-500">
              No barrier-state observations counted in the baseline window — the basis of "insufficient evidence" verdicts.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <TrendingDown size={15} className="text-amber-400" />
              <span>Post-CAPA Evidence (After Closure)</span>
            </h2>
            {isOpen && (
              <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
                Window not opened until closed
              </span>
            )}
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Evidence collected to date</span>
              <span className="font-mono text-slate-300">
                {fmtWindow(post.from_iso, isOpen ? "" : nowIso)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Configured maximum window</span>
              <span className="font-mono text-slate-300">
                {evalPeriod.postDays} days
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Barrier state</span>
              <span className="capitalize text-slate-200 font-medium">
                {isOpen ? "not evaluated" : label(post.barrier_state)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Recurrences</span>
              <span className={`font-mono font-bold ${
                (post.recurrence_count || 0) > 0 ? "text-rose-400" : "text-emerald-400"
              }`}>
                {post.recurrence_count ?? 0}
              </span>
            </div>
          </div>

          {!isOpen && (post.observation_ids || []).length > 0 ? (
            <div className="space-y-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Post-Closure Observations ({post.observation_ids.length}):
              </span>
              {post.observation_ids.map((oid) => {
                const isRecurrence = recurrenceIds.includes(oid);
                return (
                  <Link
                    key={oid}
                    to={`/app/observations/${oid}`}
                    className={`flex items-center justify-between rounded border px-3 py-1.5 text-xs transition-colors ${
                      isRecurrence
                        ? "border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
                        : "border-emerald-500/30 bg-emerald-500/5 text-slate-300 hover:border-emerald-500/50"
                    }`}
                  >
                    <span className="font-mono font-semibold flex items-center gap-1.5">
                      {isRecurrence && <RotateCcw size={11} className="text-rose-400" />}
                      {oid}
                    </span>
                    <span className="text-[10px] uppercase font-bold">
                      {isRecurrence ? "Recurrence" : "Control"}
                    </span>
                  </Link>
                );
              })}
            </div>
          ) : (
            <p className="text-[11px] italic text-slate-500">
              {isOpen
                ? "This CAPA is not closed yet. Post-closure recurrence evidence begins counting from the moment of closure."
                : "No barrier-state observations counted in the post-closure window yet."}
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-slate-400">
          {isOpen ? (
            <>
              <span className="font-semibold text-slate-200">Close this CAPA</span> to open the
              post-closure evidence window and compute the effectiveness verdict deterministically.
            </>
          ) : (
            <>
              <span className="font-semibold text-slate-200">Verdict frozen at closure.</span>{" "}
              The post-closure window ({post.window_days ?? 90} days) continues capturing
              recurrence evidence.
            </>
          )}
        </div>
        <div className="flex items-center gap-2.5">
          {isOpen ? (
            <button
              type="button"
              disabled={closing}
              onClick={() => handleClose()}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors"
            >
              <CheckCircle2 size={14} />
              <span>{closing ? "Closing…" : "Close CAPA"}</span>
            </button>
          ) : null}
          <button
            type="button"
            disabled={deleting}
            onClick={() => handleDelete()}
            className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-slate-900 px-3.5 py-2 text-[11px] font-bold text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/50 disabled:opacity-40 transition-colors"
          >
            <Trash2 size={13} />
            <span>{deleting ? "Deleting…" : "Delete CAPA"}</span>
          </button>
        </div>
      </div>

      {uniqueEvidence.length > 0 && (
        <p className="text-[11px] text-slate-500 italic">
          Evidence records used for this verdict ({uniqueEvidence.length}):{" "}
          {uniqueEvidence.join(", ")}
        </p>
      )}
    </div>
  );
}