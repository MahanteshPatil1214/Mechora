import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Network,
  ShieldAlert,
  ArrowRight,
  RotateCcw,
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  Play,
  Copy,
  ExternalLink,
  UploadCloud,
  X,
} from "lucide-react";
import { api, label } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";
import { StateBadge, SIFBadge, FieldItem } from "../components/common/StatusBadge.jsx";
import { AttentionBar } from "../components/common/AttentionBar.jsx";
import { HighlightedNarrative, EvidenceChipsList } from "../components/common/EvidenceSpan.jsx";
import { GroupingBreakdown, ExclusionList } from "../components/common/GroupingChips.jsx";

const SAMPLES = [
  {
    title: "Pipeline Flange Pressure Release",
    text: "During routine flange tightening on the gas line, the fitter did not confirm zero energy before loosening the joint and a small gas release occurred.",
    reportId: "OIL-PIPE-042",
  },
  {
    title: "Compressor Zero-Energy Omitted",
    text: "Compressor servicing: the crew opened the casing without zero-energy verification; isolation had not been done and a small gas release was observed.",
    reportId: "OIL-COMP-108",
  },
  {
    title: "Hot Work Gas Test Skipped",
    text: "Hot work area: gas testing had not been completed before grinding started; a flash fire ignited nearby rags.",
    reportId: "OIL-HOTW-019",
  },
  {
    title: "Verified Positive Control (Compliance)",
    text: "Pipeline maintenance: zero pressure was confirmed and isolation verified before the joint was opened. No issue.",
    reportId: "OIL-COMPL-003",
  },
];

export default function Analyze() {
  const [narrative, setNarrative] = useState("");
  const [reportId, setReportId] = useState("");
  const [provider, setProvider] = useState("rules");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [familyData, setFamilyData] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const resultRef = useRef(null);

  const isUploadError =
    typeof error === "string" &&
    /upload|extract|file type|size limit|limit|document/i.test(error);

  const handleAutoGenerateId = () => {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    setReportId(`OIL-OBS-${randomSuffix}`);
  };

  const handleSelectSample = (sample) => {
    setNarrative(sample.text);
    setReportId(sample.reportId);
    setError("");
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleClear = () => {
    setNarrative("");
    setReportId("");
    setError("");
    setResult(null);
    setFamilyData(null);
    setAttachedFile(null);
    setExtracting(false);
    setIsDragging(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const extractFile = async (file) => {
    setError("");
    setIsDragging(false);
    setExtracting(true);
    try {
      const body = await api.extractDocument(file);
      if (body?.text) {
        setNarrative((prev) => (prev.trim() ? prev : body.text));
      }
      setAttachedFile({
        name: body.filename,
        chars: body.character_count,
        fileType: body.file_type,
      });
    } catch (err) {
      setError(`File upload failed: ${err.message}`);
      setAttachedFile(null);
    } finally {
      setExtracting(false);
    }
  };

  const isSupportedUpload = (filename) =>
    /\.(pdf|docx|txt)$/i.test(filename || "");

  const extractUploadedFile = (file) => {
    if (!file) return;
    if (!isSupportedUpload(file.name)) {
      setError("Unsupported file type — please upload a .pdf, .docx, or .txt report.");
      return;
    }
    extractFile(file);
  };

  const handleFileChange = (e) => {
    extractUploadedFile(e.target.files?.[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    extractUploadedFile(e.dataTransfer.files?.[0]);
  };

  const handleRemoveFile = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!narrative.trim() || busy || narrative.trim().length < 8) return;

    const curReportId = reportId.trim() || `LIVE-${Date.now().toString().slice(-4)}`;
    setBusy(true);
    setError("");
    setResult(null);
    setFamilyData(null);

    try {
      const res = await api.analyze({
        report_id: curReportId,
        narrative: narrative.trim(),
        provider: provider,
      });

      setResult(res);

      if (res.precursor_family_id) {
        try {
          const fam = await api.family(res.precursor_family_id);
          setFamilyData(fam);
        } catch {
          /* ignore */
        }
      }

      // Smooth scroll to results
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (err) {
      setError(err.message || "Analysis failed. Please check input observation narrative.");
    } finally {
      setBusy(false);
    }
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      handleSubmit();
    }
  };

  const event = result?.event || {};
  const fieldEvidence = event.field_evidence || {};

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* 1. Standard Page Header */}
      <PageHeader
        title="Safety Observation Analysis Workbench"
        description="Submit observation narratives to extract canonical safety events, identify grounded evidence spans, and detect precursor signatures."
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/app/observations"
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <Search size={14} className="text-slate-400" />
              <span>Browse Observations</span>
            </Link>
          </div>
        }
      />

      {/* 2. Top Section: Narrative Input Form */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Form Top Controls: Report ID & Provider */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Report Identifier (Optional)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. OIL-PIPE-042"
                  value={reportId}
                  onChange={(e) => setReportId(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleAutoGenerateId}
                  className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                >
                  Generate ID
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Inference Provider
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-200 focus:border-amber-500 focus:outline-none"
              >
                <option value="rules">Deterministic Rules Engine (Default / Recommended)</option>
                <option value="llm">Gemini LLM (requires configured API key)</option>
                <option value="auto">Auto — Gemini if key is set, else rules</option>
              </select>
            </div>
          </div>

          {/* Narrative Textarea */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Observation Narrative
              </label>
              <span className="text-[11px] text-slate-500 font-mono">
                {narrative.length} characters
              </span>
            </div>
            <textarea
              ref={textareaRef}
              rows={4}
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={busy}
              placeholder="Paste or write the safety observation narrative here (e.g., 'During routine flange maintenance on the gas line, the fitter opened the flange before verifying zero energy, resulting in a small gas release...')"
              className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:outline-none leading-relaxed transition-colors"
            />
          </div>

          {/* File / Report Attachment */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Attach Report File (Optional)
            </label>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              disabled={busy || extracting}
            />
            {attachedFile ? (
              <div className="flex items-center justify-between gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileText size={15} className="text-amber-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-slate-200 truncate">{attachedFile.name}</div>
                    <div className="text-[10px] font-mono text-slate-400">
                      {attachedFile.fileType?.toUpperCase()} · {attachedFile.chars} characters extracted
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-rose-400 transition-colors flex-shrink-0"
                  aria-label="Remove attached file"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <div
                role="button"
                tabIndex={0}
                onClick={() => {
                  if (!busy && !extracting) {
                    fileInputRef.current?.click();
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    if (!busy && !extracting) {
                      fileInputRef.current?.click();
                    }
                  }
                }}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`flex flex-col items-center justify-center rounded-lg border border-dashed px-4 py-4 text-center transition-colors ${
                  isDragging
                    ? "border-amber-500 bg-slate-900"
                    : "border-slate-700 bg-slate-950/60 hover:border-slate-600 hover:bg-slate-900/60"
                } ${busy || extracting ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <UploadCloud
                  size={18}
                  className={`mb-1.5 ${isDragging ? "text-amber-400" : "text-slate-400"}`}
                />
                <div className="text-xs text-slate-300">
                  {extracting ? (
                    <>Extracting text…</>
                  ) : (
                    <>
                      Drag & drop a report file here, or{" "}
                      <span className="text-amber-400 font-medium underline underline-offset-2">browse</span>
                    </>
                  )}
                </div>
                <div className="text-[11px] font-mono text-slate-500 mt-1">
                  Supported formats: PDF, DOCX, TXT (Max 15MB)
                </div>
              </div>
            )}
            <p className="mt-1 text-[10px] text-slate-500">
              Extracted text is loaded into the narrative box below — review and edit it before analyzing.
            </p>
            {isUploadError && (
              <p className="mt-2 flex items-start gap-1.5 text-[11px] text-rose-300">
                <AlertTriangle size={13} className="text-rose-400 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </p>
            )}
          </div>

          {/* Sample Scenarios Buttons */}
          <div className="space-y-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Load Sample Scenarios:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {SAMPLES.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectSample(s)}
                  className="rounded-lg border border-slate-800 bg-slate-950/80 p-2 text-left hover:border-slate-700 hover:bg-slate-850 transition-colors group"
                >
                  <div className="text-xs font-medium text-slate-200 group-hover:text-amber-400 transition-colors">
                    {s.title}
                  </div>
                  <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                    {s.text}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800">
            <div className="text-xs text-slate-400 flex items-center gap-1.5">
              <kbd className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                Ctrl
              </kbd>
              <span>+</span>
              <kbd className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400">
                Enter
              </kbd>
              <span>to run analysis</span>
            </div>

            <div className="flex items-center gap-2.5">
              {(narrative || result || error) && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <RotateCcw size={13} />
                  <span>Clear</span>
                </button>
              )}

              <button
                type="submit"
                disabled={busy || narrative.trim().length < 8}
                className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-amber-500 disabled:opacity-40 transition-colors shadow-sm"
              >
                {busy ? (
                  <span>Analyzing Observation…</span>
                ) : (
                  <>
                    <Play size={13} className="fill-current" />
                    <span>Analyze Observation</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 flex items-start gap-2">
          <AlertTriangle size={16} className="text-rose-400 mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-semibold">
              {isUploadError ? "File Upload Failed" : "Analysis Failed"}
            </div>
            <p className="mt-0.5 text-rose-300/80">{error}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {busy && (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 space-y-4 animate-pulse">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="h-4 w-48 bg-slate-800 rounded" />
            <div className="h-4 w-24 bg-slate-800 rounded" />
          </div>
          <div className="h-20 bg-slate-950 rounded" />
          <div className="grid grid-cols-4 gap-3">
            <div className="h-16 bg-slate-950 rounded" />
            <div className="h-16 bg-slate-950 rounded" />
            <div className="h-16 bg-slate-950 rounded" />
            <div className="h-16 bg-slate-950 rounded" />
          </div>
        </div>
      )}

      {/* 3. Results Section (Rendered directly below the form) */}
      {result && (
        <div ref={resultRef} className="space-y-6 pt-2">
          {/* Section Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h2 className="text-base font-bold text-white">Analysis Results Workbench</h2>
              <p className="text-xs text-slate-400">
                Structured canonical extraction and grounded precursor intelligence.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-slate-400">
                {result.report_id}
              </span>
              <span className="text-slate-600">·</span>
              <span className="font-mono text-xs text-slate-500">{result.id}</span>
            </div>
          </div>

          {/* Result Card: Header & Metadata */}
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">
                  SIF Classification
                </span>
                <div className="mt-1">
                  <SIFBadge value={event.sif?.classification} />
                </div>
              </div>
              <div className="border-l border-slate-800 pl-3">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">
                  Barrier State
                </span>
                <div className="mt-1">
                  <StateBadge value={event.barrier_state} />
                </div>
              </div>
              <div className="border-l border-slate-800 pl-3">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">
                  Extraction Confidence
                </span>
                <div className="mt-1 font-mono text-xs font-bold text-white">
                  {Math.round((event.confidence ?? 0.9) * 100)}%
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-400">
              <span className="text-[10px] uppercase font-bold text-slate-500 block text-right">
                Provider
              </span>
              <span className="font-mono text-slate-300">{result.provider || "rules"}</span>
              {result.fallback_used && (
                <div className="mt-1 text-[11px] text-amber-400 border-t border-slate-800/70 pt-1">
                  <span className="font-semibold">⚠ Fallback</span>
                  <span className="text-amber-300/80">
                    {" deterministic rules engine"}
                    {result.fallback_reason ? ` — ${result.fallback_reason}` : ""}.
                  </span>
                </div>
              )}
              {(result.warnings || []).length > 0 && (
                <ul className="mt-1 text-[11px] text-slate-400 space-y-0.5">
                  {(result.warnings || []).map((w, i) => (
                    <li key={i} className="before:content-['·'] before:mr-1"> {w}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Grounded Evidence Section */}
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Grounded Evidence Narrative
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Exact in-situ sentence fragments that grounded the canonical extraction.
                </p>
              </div>
              <span className="text-emerald-400 font-mono text-xs font-medium">
                ✓ Evidence Grounded
              </span>
            </div>

            {/* In-Situ Highlighted Narrative */}
            <div className="rounded-lg border border-slate-800/80 bg-slate-950 p-4">
              <HighlightedNarrative
                narrative={event.narrative || narrative}
                fieldEvidence={fieldEvidence}
                className="text-sm leading-relaxed"
              />
            </div>

            {/* Extracted Evidence Chips Legend */}
            <div className="pt-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1.5">
                Extracted Evidence Spans by Field:
              </span>
              <EvidenceChipsList fieldEvidence={fieldEvidence} />
            </div>
          </div>

          {/* Canonical Structured Safety Event Grid */}
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Canonical Structured Safety Event
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Normalized ontology concepts mapped according to OIL safety taxonomy.
                </p>
              </div>
              <span className="rounded bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 text-[10px] font-semibold text-sky-400">
                Pydantic Validated
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
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
                <span className="text-[10px] uppercase font-bold text-slate-400">Barrier State</span>
                <div className="mt-1">
                  <StateBadge value={event.barrier_state} />
                </div>
              </div>
            </div>
          </div>

          {/* Precursor Signature & Life-Saving Rules */}
          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block">
                  Structural Precursor Signature
                </span>
                <div className="font-mono text-xs sm:text-sm font-bold text-amber-400 mt-0.5">
                  {label(event.energy)} + {label(event.barrier)} + {label(event.barrier_state)}
                </div>
              </div>
              <div className="text-xs text-slate-400">
                Deterministic signature vector
              </div>
            </div>

            {event.life_saving_rules?.length > 0 && (
              <div className="border-t border-slate-800 pt-2.5">
                <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                  Applicable IOGP Life-Saving Rules:
                </span>
                <div className="flex flex-wrap gap-1.5">
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

          {/* SIF Potential Rationale */}
          {event.sif && (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 space-y-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  SIF Potential Assessment & Rationale
                </span>
                <SIFBadge value={event.sif.classification} />
              </div>
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {event.sif.reason}
              </p>
              {event.sif.supporting_evidence?.length > 0 && (
                <ul className="text-xs text-slate-400 space-y-1 pt-1">
                  {event.sif.supporting_evidence.map((line, idx) => (
                    <li key={idx} className="flex items-center gap-1.5">
                      <span className="text-amber-400 font-bold">•</span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              )}
              {event.sif.model_note && (
                <p className="text-[11px] italic text-slate-500 pt-1 border-t border-slate-800/60 mt-2">
                  {event.sif.model_note}
                </p>
              )}
            </div>
          )}

          {/* Precursor Family Match */}
          {result.precursor_family_id ? (
            <div className="rounded-lg border border-amber-500/30 bg-slate-900 p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-amber-400">
                      {result.precursor_family_id}
                    </span>
                    <span className="rounded bg-rose-500/15 border border-rose-500/30 px-1.5 py-0.2 text-[10px] font-bold text-rose-300 uppercase">
                      Recurring Precursor
                    </span>
                  </div>
                  <h3 className="mt-1 text-base font-bold text-white">
                    {familyData?.name || "Energy Isolation Verification Failure"}
                  </h3>
                </div>

                <Link
                  to={`/app/families/${result.precursor_family_id}`}
                  className="flex items-center gap-1 text-xs font-semibold text-amber-400 hover:text-amber-300 hover:underline"
                >
                  <span>Explore Family Intelligence</span>
                  <ArrowRight size={13} />
                </Link>
              </div>

              {familyData && (
                <>
                  <AttentionBar
                    value={familyData.attention_signal}
                    showBasis={true}
                    basis={familyData.attention_basis}
                  />

                  {/* WHY GROUPED */}
                  {familyData.grouping_evidence && (
                    <GroupingBreakdown
                      evidence={familyData.grouping_evidence}
                      title={
                        familyData.recurring
                          ? "WHY THESE OBSERVATIONS ARE GROUPED (Structural Commonalities)"
                          : "WHY THIS REPORT QUALIFIES AS A PRECURSOR CANDIDATE"
                      }
                      subtitle={
                        familyData.recurring
                          ? "Per-dimension comparison over family members"
                          : "Single-report structural profile"
                      }
                    />
                  )}

                  {/* WHY NOT GROUPED */}
                  {familyData.exclusions && (
                    <ExclusionList exclusions={familyData.exclusions} />
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4 text-xs text-slate-400">
              <span className="font-semibold text-slate-200">No Precursor Family Match: </span>
              This observation did not meet the structural similarity threshold (0.65) to merge into an
              existing recurring precursor family. It is stored as an independent observation.
            </div>
          )}

          {/* Action Footer */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="text-xs text-slate-500 italic">
              Prototype HSE Attention Signal — decision support, not an official OIL risk score.
            </div>

            <div className="flex items-center gap-3">
              <Link
                to={`/app/observations/${result.id}`}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-850 hover:text-white transition-colors"
              >
                <FileText size={14} />
                <span>Open Stored Record</span>
              </Link>
              {result.precursor_family_id && (
                <Link
                  to={`/app/families/${result.precursor_family_id}`}
                  className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-amber-500 transition-colors shadow-sm"
                >
                  <Network size={14} />
                  <span>View Family Intelligence</span>
                </Link>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
