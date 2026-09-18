import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCheck2,
  ExternalLink,
  HelpCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Check,
} from "lucide-react";
import { api, label } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge, ValidationBadge } from "../components/common/StatusBadge.jsx";
import { HighlightedNarrative } from "../components/common/EvidenceSpan.jsx";

export default function HSEReview() {
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("needs_review"); // needs_review | validated | rejected | all
  const [updatingId, setUpdatingId] = useState(null);
  const [notice, setNotice] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.observations({ limit: 100 });
      setObservations(res.observations || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleValidation = async (obsId, status) => {
    setUpdatingId(obsId);
    try {
      await api.updateValidation(obsId, status);
      setObservations((prev) =>
        prev.map((o) => (o.id === obsId ? { ...o, validation: status } : o)),
      );
      setNotice(`Observation ${obsId} marked as ${status.toUpperCase()}. Human audit recorded.`);
      setTimeout(() => setNotice(""), 4000);
    } catch {
      /* ignore */
    } finally {
      setUpdatingId(null);
    }
  };

  // Filter observations based on tab
  const filtered = observations.filter((o) => {
    const isNeedsReview =
      o.validation === "pending" ||
      o.event?.sif?.classification === "needs_review" ||
      o.event?.evidence_status === "needs_review" ||
      (o.event?.confidence ?? 1) < 0.7;

    if (tab === "needs_review") return isNeedsReview && o.validation !== "validated";
    if (tab === "validated") return o.validation === "validated";
    if (tab === "rejected") return o.validation === "rejected";
    return true; // all
  });

  const needsReviewCount = observations.filter(
    (o) =>
      (o.validation === "pending" ||
        o.event?.sif?.classification === "needs_review" ||
        o.event?.evidence_status === "needs_review") &&
      o.validation !== "validated",
  ).length;

  const validatedCount = observations.filter((o) => o.validation === "validated").length;
  const rejectedCount = observations.filter((o) => o.validation === "rejected").length;

  return (
    <div className="space-y-6">
      {/* Enterprise Page Header */}
      <PageHeader
        title="HSE Human-in-the-Loop Review Queue"
        subtitle="Validate ambiguous narratives, low-confidence extractions, or unverified precursor matches."
        breadcrumbs={[{ label: "HSE Review Queue" }]}
        actions={
          <div className="flex items-center gap-2.5">
            {needsReviewCount > 0 && (
              <span className="rounded-full bg-rose-500/20 border border-rose-500/40 px-3 py-1 text-xs font-bold text-rose-300">
                {needsReviewCount} Pending Review
              </span>
            )}
            <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs text-sky-300">
              <ShieldCheck size={14} />
              <span>Decision Support · Human Governed</span>
            </div>
          </div>
        }
      />

      {notice && (
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{notice}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex border-b border-slate-800 gap-6 text-xs font-bold">
        <button
          type="button"
          onClick={() => setTab("needs_review")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            tab === "needs_review"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Needs HSE Review</span>
          <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">
            {needsReviewCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setTab("validated")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            tab === "validated"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Validated Records</span>
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
            {validatedCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setTab("rejected")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            tab === "rejected"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>Rejected / Separated</span>
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
            {rejectedCount}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setTab("all")}
          className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
            tab === "all"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>All Observations</span>
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
            {observations.length}
          </span>
        </button>
      </div>

      {/* Review Cards Feed */}
      {loading ? (
        <div className="py-16 text-center text-xs text-slate-500 font-mono">
          Loading review queue items...
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center space-y-3">
          <CheckCircle2 size={32} className="mx-auto text-emerald-400" />
          <h3 className="text-sm font-bold text-white">Queue Empty</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {tab === "needs_review"
              ? "All observations have either been validated or meet high-confidence automated extraction criteria."
              : `No observations found in ${tab.replace("_", " ")} category.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((obs) => {
            const event = obs.event || {};
            const isPending = obs.validation === "pending";

            // Determine specific reasons for review
            const reviewReasons = [];
            if (event.sif?.classification === "needs_review") {
              reviewReasons.push("SIF potential requires HSE confirmation");
            }
            if (event.evidence_status === "needs_review") {
              reviewReasons.push("Ungrounded inference detected in narrative");
            }
            if ((event.confidence ?? 1) < 0.7) {
              reviewReasons.push(
                `Low extraction confidence (${Math.round((event.confidence ?? 0.5) * 100)}%)`,
              );
            }
            if (event.barrier === "unknown" || event.barrier_state === "unknown") {
              reviewReasons.push("Barrier or barrier failure state missing/unknown");
            }
            if (reviewReasons.length === 0 && isPending) {
              reviewReasons.push("Routine human-in-the-loop audit sample");
            }

            return (
              <div
                key={obs.id}
                className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4 shadow-sm"
              >
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-sm font-bold text-white">
                      {obs.report_id || obs.id}
                    </span>
                    <span className="text-slate-600">·</span>
                    <span className="font-mono text-xs text-slate-500">{obs.id}</span>
                    <span className="text-slate-600">·</span>
                    <span className="text-xs text-slate-400">
                      {new Date(obs.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <StateBadge value={event.barrier_state} />
                    <SIFBadge value={event.sif?.classification} />
                    <ValidationBadge status={obs.validation} />
                  </div>
                </div>

                {/* Routing Reason Flag */}
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-200 flex items-start gap-2">
                  <HelpCircle size={15} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="font-bold text-amber-300 uppercase text-[10px] block">
                      Why routed for HSE review:
                    </span>
                    <span>{reviewReasons.join(" · ")}</span>
                  </div>
                </div>

                {/* Grounded Narrative */}
                <div className="space-y-1.5">
                  <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
                    Observation Narrative & Grounded In-Situ Evidence
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
                    <HighlightedNarrative
                      narrative={obs.narrative}
                      fieldEvidence={event.field_evidence}
                      className="text-xs leading-relaxed"
                    />
                  </div>
                </div>

                {/* Canonical Extracted Fields */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                  <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Activity</span>
                    <p className="font-semibold text-slate-200 capitalize mt-0.5">
                      {label(event.activity || "Operations")}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Hazard / Energy</span>
                    <p className="font-semibold text-slate-200 capitalize mt-0.5">
                      {label(event.energy || "Unknown")}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Safety Barrier</span>
                    <p className="font-semibold text-slate-200 capitalize mt-0.5">
                      {label(event.barrier || "Unknown")}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Exposure</span>
                    <p className="font-semibold text-slate-200 capitalize mt-0.5">
                      {label(event.exposure || "Direct consequence")}
                    </p>
                  </div>
                </div>

                {/* SIF Assessment & Precursor Family Grouping */}
                <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-lg border border-slate-800 bg-slate-950/60 p-2.5 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500">SIF Assessment:</span>
                    <SIFBadge value={event.sif?.classification} />
                    <span className="text-slate-300 text-[11px]">
                      {event.sif?.reason || "Classification routed for human HSE confirmation."}
                    </span>
                  </div>
                  {obs.precursor_family_id && (
                    <div className="flex items-center gap-1.5 font-mono text-[11px]">
                      <span className="text-slate-500">Precursor Family:</span>
                      <Link
                        to={`/app/families/${obs.precursor_family_id}`}
                        className="text-amber-400 hover:underline font-bold"
                      >
                        {obs.precursor_family_id}
                      </Link>
                    </div>
                  )}
                </div>

                {/* Interactive Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <Link
                    to={`/app/observations/${obs.id}`}
                    className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 hover:underline"
                  >
                    <span>Inspect Full Evidence & Modify</span>
                    <ArrowRight size={13} />
                  </Link>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={updatingId === obs.id || obs.validation === "validated"}
                      onClick={() => handleValidation(obs.id, "validated")}
                      className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors shadow-sm"
                    >
                      <Check size={13} />
                      <span>Confirm / Validate</span>
                    </button>

                    <button
                      type="button"
                      disabled={updatingId === obs.id || obs.validation === "rejected"}
                      onClick={() => handleValidation(obs.id, "rejected")}
                      className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-rose-300 hover:border-rose-500/50 hover:bg-rose-500/10 disabled:opacity-40 transition-colors"
                    >
                      <XCircle size={13} />
                      <span>Reject / Separate</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
