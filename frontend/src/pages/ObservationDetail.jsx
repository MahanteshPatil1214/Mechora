import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Network,
  ExternalLink,
  FileCheck2,
  Shield,
  Layers,
  Trash2,
} from "lucide-react";
import { api, label, reportTypeLabel } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge, ValidationBadge, FieldItem } from "../components/common/StatusBadge.jsx";
import { HighlightedNarrative, EvidenceChipsList } from "../components/common/EvidenceSpan.jsx";
import { GroupingBreakdown, ExclusionList } from "../components/common/GroupingChips.jsx";
import { AttentionBar } from "../components/common/AttentionBar.jsx";

export default function ObservationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [obs, setObs] = useState(null);
  const [family, setFamily] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .observation(id)
      .then((data) => {
        setObs(data);
        if (data?.precursor_family_id) {
          api
            .family(data.precursor_family_id)
            .then(setFamily)
            .catch(() => {});
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const handleValidation = async (status) => {
    setValidating(true);
    try {
      await api.updateValidation(obs.id, status);
      setObs((prev) => ({ ...prev, validation: status }));
      setActionSuccess(`Validation status updated to "${status.toUpperCase()}". Decision saved.`);
      setTimeout(() => setActionSuccess(""), 4000);
    } catch {
      /* ignore */
    } finally {
      setValidating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete observation "${obs.report_id}"? This permanently removes the record and rebuilds precursor families.`)) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteObservation(obs.id);
      navigate("/app/observations", {
        state: { deleted: obs.report_id, _t: Date.now() },
      });
    } catch {
      setActionSuccess("Failed to delete observation. Please try again.");
      setTimeout(() => setActionSuccess(""), 4000);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-16 text-center text-xs text-slate-500">
        Loading observation details…
      </div>
    );
  }

  if (!obs) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-12 text-center space-y-4">
        <h2 className="text-base font-bold text-white">Observation Record Not Found</h2>
        <p className="text-xs text-slate-400">The requested observation ID could not be located in the database.</p>
        <Link to="/app/observations" className="text-xs font-semibold text-amber-400 hover:underline">
          ← Return to Observations Browser
        </Link>
      </div>
    );
  }

  const event = obs.event || {};
  const fieldEvidence = event.field_evidence || {};

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Page Header with Breadcrumb */}
      <PageHeader
        breadcrumb={
          <Link
            to="/app/observations"
            className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft size={13} />
            <span>Back to Observations</span>
          </Link>
        }
        title={obs.report_id}
        description={`${reportTypeLabel(obs.report_type)} · Observation record ${obs.id} · Logged ${new Date(obs.created_at).toLocaleString()} · Provider: ${obs.provider || "rules"}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StateBadge value={event.barrier_state} />
            <SIFBadge value={event.sif?.classification} />
            <ValidationBadge status={obs.validation} />
          </div>
        }
      />

      {/* Success Notification */}
      {actionSuccess && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-400 flex-shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* 2. Main Two-Column Evidence-First Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Original Narrative with Grounded Evidence (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <FileCheck2 size={15} className="text-amber-400" />
                <span>Original Observation Narrative</span>
              </h2>
              <span className="text-emerald-400 font-mono text-[11px]">
                In-Situ Grounded
              </span>
            </div>

            {/* Highlighted Narrative */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
              <HighlightedNarrative
                narrative={obs.narrative}
                fieldEvidence={fieldEvidence}
                className="text-sm leading-relaxed"
              />
            </div>

            {/* Extracted Evidence Chips */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Extracted Evidence Spans by Field:
              </span>
              <EvidenceChipsList fieldEvidence={fieldEvidence} />
            </div>

            <div className="text-[11px] text-slate-500 italic border-t border-slate-800/80 pt-2.5">
              Highlighted spans show the exact sentence fragments that triggered canonical extraction.
            </div>
          </div>

          {/* SIF Assessment & Rationale */}
          {event.sif && (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  SIF Potential Assessment & Rationale
                </span>
                <SIFBadge value={event.sif.classification} />
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">{event.sif.reason}</p>
              {event.sif.supporting_evidence?.length > 0 && (
                <ul className="space-y-1 text-xs text-slate-400 pt-1">
                  {event.sif.supporting_evidence.map((line, idx) => (
                    <li key={idx} className="flex items-center gap-1.5">
                      <span className="text-amber-400 font-bold">•</span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              )}
              {event.sif.model_note && (
                <p className="text-[11px] italic text-slate-500 pt-2 border-t border-slate-800/60 mt-1">
                  {event.sif.model_note}
                </p>
              )}
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Canonical Structured Safety Event (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Canonical Structured Safety Event
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Normalized concepts with EXPLICIT vs INFERRED grounding tags
                </p>
              </div>
              <span className="rounded bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 text-[10px] font-semibold text-sky-400">
                Pydantic Validated
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <FieldItem
                label="Activity"
                value={event.activity}
                source="canonical"
                basis={event.field_basis?.activity}
                evidence={fieldEvidence.activity}
              />
              <FieldItem
                label="Task Phase"
                value={event.task_phase}
                source="canonical"
                basis={event.field_basis?.task_phase}
                evidence={fieldEvidence.task_phase}
              />
              <FieldItem
                label="Hazardous Energy"
                value={event.energy}
                source="inferred"
                basis={event.field_basis?.energy}
                evidence={fieldEvidence.energy}
              />
              <FieldItem
                label="Required Barrier"
                value={event.barrier}
                source="inferred"
                basis={event.field_basis?.barrier}
                evidence={fieldEvidence.barrier}
              />
              <FieldItem
                label="Exposure Mechanism"
                value={event.exposure}
                source="inferred"
                basis={event.field_basis?.exposure}
                evidence={fieldEvidence.exposure}
              />
              <FieldItem
                label="Potential Consequence"
                value={event.potential_consequence}
                source="inferred"
                basis={event.field_basis?.potential_consequence}
              />
              <FieldItem
                label="Location"
                value={event.location}
                source="canonical"
                basis={event.field_basis?.location}
              />
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 flex flex-col justify-between">
                <span className="text-[10px] uppercase font-bold text-slate-400">
                  Barrier State
                </span>
                <div className="mt-1">
                  <StateBadge value={event.barrier_state} />
                </div>
              </div>
            </div>

            {/* Precursor Signature & Life-Saving Rules */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs space-y-2">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 block">
                  Structural Precursor Signature:
                </span>
                <div className="font-mono text-xs font-bold text-amber-400 mt-0.5">
                  {label(event.energy)} + {label(event.barrier)} + {label(event.barrier_state)}
                </div>
              </div>
              {event.life_saving_rules?.length > 0 && (
                <div className="border-t border-slate-800 pt-2">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                    Applicable IOGP Life-Saving Rules:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {event.life_saving_rules.map((rule) => (
                      <span
                        key={rule}
                        className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-300"
                      >
                        {label(rule)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* HSE Human Validation Actions */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  HSE Human-in-the-Loop Validation
                </span>
                <ValidationBadge status={obs.validation} />
              </div>
              <p className="text-xs text-slate-400">
                Confirm whether this safety observation was accurately extracted and grouped.
              </p>
              <div className="flex items-center gap-2.5 pt-1">
                <button
                  type="button"
                  disabled={validating || obs.validation === "validated"}
                  onClick={() => handleValidation("validated")}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors"
                >
                  <CheckCircle2 size={14} />
                  <span>Validate / Confirm</span>
                </button>
                <button
                  type="button"
                  disabled={validating || obs.validation === "rejected"}
                  onClick={() => handleValidation("rejected")}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-300 hover:bg-rose-500/20 disabled:opacity-40 transition-colors"
                >
                  <XCircle size={14} />
                  <span>Reject / Separate</span>
                </button>
              </div>
              <div className="border-t border-slate-800 pt-3 flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-500 italic">
                  Permanently removes this record and rebuilds precursor families.
                </span>
                <button
                  type="button"
                  disabled={deleting}
                  onClick={() => handleDelete()}
                  className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-slate-900 px-3 py-1.5 text-[11px] font-bold text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/50 disabled:opacity-40 transition-colors"
                >
                  <Trash2 size={13} />
                  <span>{deleting ? "Deleting…" : "Delete Observation"}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. LOWER SECTION: Precursor Family Membership & Comparison */}
      {obs.precursor_family_id && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <Network size={16} className="text-amber-400" />
                {family?.recurring ? (
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Associated Precursor Family: {family?.name || obs.precursor_family_id}
                  </h3>
                ) : (
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Candidate Precursor / Pending Family Assignment
                  </h3>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {family?.recurring
                  ? `Grouped based on identical failed barrier (${label(event.barrier)}) and hazardous energy.`
                  : `Only one report so far — a recurring precursor family needs ${"\u2265"}2 structurally compatible reports sharing this failed barrier (${label(event.barrier)}) and energy.`}
              </p>
            </div>
            <Link
              to={`/app/families/${obs.precursor_family_id}`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-amber-500 transition-colors shadow-sm"
            >
              <span>Explore Family Intelligence</span>
              <ExternalLink size={13} />
            </Link>
          </div>

          {family && (
            <div className="space-y-4">
              <AttentionBar
                value={family.attention_signal}
                showBasis={true}
                basis={family.attention_basis}
              />
              {family.grouping_evidence && (
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
              )}
              {family.exclusions && (
                <ExclusionList exclusions={family.exclusions} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
