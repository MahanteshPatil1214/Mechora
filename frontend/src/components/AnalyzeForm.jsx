import { useState } from "react";
import { api, label } from "../api.js";
import { Field, StateBadge, SIFBadge, NeedsReviewBadge, SifPanel, EvidenceChips, FamilyTypeBadge } from "./Badge.jsx";

function potentialBasis(event) {
  if (!event || event.potential_consequence_basis !== "model_inference") return "";
  const parts = [];
  if (event.barrier && event.barrier !== "unknown") parts.push(`${label(event.barrier)} (${label(event.barrier_state)})`);
  if (event.energy && event.energy !== "unknown") parts.push(label(event.energy));
  if (event.exposure && event.exposure !== "unknown") parts.push(label(event.exposure));
  return parts.join(" + ");
}

const SAMPLES = [
  "Went to carry out repair on the crude line flange, fitter opened the drain valve before the line was proven depressurized. There was a sudden release of residual pressure and fluid splashed out, no one injured but coveralls were soaked.",
  "Hot work started near the storage tank while the gas test was still pending; strong smell of fuel vapour in the area and the fire watch had not been posted. Supervisor stopped the work.",
  "Two workers entered the pump pit to inspect the sump without completing the atmospheric test, the gas detector was left on the surface. They complained of dizziness and were pulled out.",
  "Crane was lifting the exchanger bundle over the laydown area, the banksman stood inside the swing radius and the exclusion zone tape was not set out. Load swung when the wind gusted.",
  "While replacing the motor on the transfer pump, the electrician opened the breaker, applied his own padlock and verified zero energy before touching the terminals. Good practice observed.",
  "Found the top scaffold platform handrail missing after the boarding was changed; the worker was tied off to the anchor point. Scaffold was tagged out of service.",
  "Pigging operation started without confirming the launcher was isolated from the main line; the kicker valve was found cracked open and the blind was not installed.",
  "Tank cleaning entry: oxygen level checked at 20.9% and LEL below 10% before entry, permit conditions satisfied and entry was logged with retrieval line in place.",
];

export default function AnalyzeForm({ onAnalyzed }) {
  const [narrative, setNarrative] = useState("");
  const [reportId, setReportId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function submit(ev) {
    ev.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.analyze({
        report_id: reportId || `LIVE-${Date.now()}`,
        narrative,
        provider: "rules",
      });
      setResult(res);
      onAnalyzed(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const derivedType = result
    ? result.event.barrier_state === "verified"
      ? "controlled"
      : result.event.needs_review || result.event.barrier_state === "unknown"
      ? "needs_review"
      : "precursor"
    : "precursor";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
        Analyze observation
      </h2>
      <form onSubmit={submit} className="mt-3 flex flex-col gap-3">
        <input
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
          placeholder="Report ID (optional)"
          value={reportId}
          onChange={(e) => setReportId(e.target.value)}
        />
        <textarea
          className="min-h-32 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
          placeholder="Paste an HSE observation narrative…"
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
        />
        <div className="flex flex-wrap justify-between gap-2">
          <div className="flex flex-wrap gap-1.5">
            {SAMPLES.map((s) => (
              <button
                key={s.slice(0, 24)}
                type="button"
                onClick={() => setNarrative(s)}
                className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-sky-500 hover:text-sky-300"
              >
                Sample {SAMPLES.indexOf(s) + 1}
              </button>
            ))}
          </div>
          <button
            type="submit"
            disabled={busy || narrative.trim().length < 8}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-40"
          >
            {busy ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </form>
      {error && (
        <p className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </p>
      )}
      {result && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-slate-400">
              {result.report_id} · {result.id} · provider={result.provider}
            </span>
            <div className="flex items-center gap-2">
              {result.event.needs_review && (
                <NeedsReviewBadge missingFields={result.event.missing_fields} />
              )}
              <FamilyTypeBadge type={derivedType} />
              <StateBadge value={result.event.barrier_state} />
              <SIFBadge value={result.event.sif.classification} />
            </div>
          </div>
          {result.event.needs_review && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 space-y-1">
              <div className="font-semibold text-amber-300">⚠ Precursor Needs HSE Human Review</div>
              <p>
                Critical safety attributes could not be confirmed from the narrative text alone:{" "}
                <span className="font-mono text-amber-100">
                  {result.event.missing_fields?.join(", ")}
                </span>
                . In accordance with safety logic, unverified critical fields are held for review rather than guessed.
              </p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {(() => {
              const fb = result.event.field_basis || {};
              return [
                <Field
                  key="activity"
                  name="Activity"
                  value={result.event.activity}
                  evidence={result.event.field_evidence?.activity}
                  basis={fb.activity}
                />,
                <Field
                  key="phase"
                  name="Task Phase"
                  value={result.event.task_phase}
                  evidence={result.event.field_evidence?.task_phase}
                  basis={fb.task_phase}
                />,
                <Field
                  key="energy"
                  name="Energy / Hazard"
                  value={result.event.energy}
                  evidence={result.event.field_evidence?.energy}
                  basis={fb.energy}
                />,
                <Field
                  key="barrier"
                  name="Barrier"
                  value={result.event.barrier}
                  evidence={result.event.field_evidence?.barrier}
                  basis={fb.barrier}
                />,
                <Field
                  key="exposure"
                  name="Exposure"
                  value={result.event.exposure}
                  evidence={result.event.field_evidence?.exposure}
                  basis={fb.exposure}
                />,
                <div
                  key="barrierState"
                  className="flex flex-col gap-1 rounded-md border border-slate-800/80 bg-slate-900/60 p-2 min-w-[140px]"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                      Barrier State
                    </span>
                    <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-500 lowercase">
                      negation
                    </span>
                  </div>
                  <StateBadge value={result.event.barrier_state} />
                  {fb.barrier_state && fb.barrier_state !== "unknown" && (
                    <div className="flex items-center gap-1">
                      <span
                        className={
                          fb.barrier_state === "explicit"
                            ? "rounded border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-300"
                            : "rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-300"
                        }
                      >
                        {fb.barrier_state === "explicit" ? "EXPLICIT" : "INFERRED"}
                      </span>
                      <span className="text-[9px] italic text-slate-500">
                        {fb.barrier_state === "explicit" ? "stated in report" : "no direct span — derived"}
                      </span>
                    </div>
                  )}
                  {result.event.field_evidence?.barrier_state ? (
                    <div className="mt-0.5 flex items-start gap-1 text-[11px] text-sky-400 font-mono italic leading-tight">
                      <span className="text-[10px] font-sans font-semibold uppercase tracking-tight text-sky-500/80 not-italic">
                        evidence:
                      </span>
                      <span className="break-words">“{result.event.field_evidence.barrier_state}”</span>
                    </div>
                  ) : (
                    <span className="text-[10px] text-slate-600 italic">no direct span</span>
                  )}
                </div>,
                <Field
                  key="potential"
                  name="Potential"
                  value={result.event.potential_consequence}
                  evidence={result.event.field_evidence?.potential_consequence}
                  basis={result.event.potential_consequence_basis}
                  basisDetail={potentialBasis(result.event)}
                />,
                <Field
                  key="actual"
                  name="Actual"
                  value={result.event.actual_consequence}
                  evidence={result.event.field_evidence?.actual_consequence}
                  basis={fb.actual_consequence}
                />,
                <Field
                  key="location"
                  name="Location"
                  value={result.event.location}
                  evidence={result.event.field_evidence?.location}
                  basis={fb.location}
                  isCanonical={false}
                />,
              ];
            })()}
          </div>
          <div className="text-xs text-slate-400">
            Life-saving rules:{" "}
            {result.event.life_saving_rules?.map((r) => (
              <code key={r} className="mr-1">{r}</code>
            ))}
          </div>
          {result.event?.needs_review || !result.precursor_family_id || result.precursor_family_id === "UNASSIGNED / PENDING REVIEW" ? (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-amber-400 font-bold">Safety Family:</span>
                <span className="text-amber-200 font-mono font-bold">UNASSIGNED / PENDING REVIEW</span>
              </div>
              <span className="text-[10px] text-amber-300/80 italic">
                Critical safety fields missing — held for HSE specialist review before family assignment
              </span>
            </div>
          ) : (
            <div className="rounded-md border border-sky-500/30 bg-sky-500/10 p-2.5 text-xs flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-wider text-sky-400 font-bold">Assigned Safety Family:</span>
                <span className="text-sky-200 font-mono font-bold">{result.precursor_family_id}</span>
              </div>
              <span className="text-[10px] text-slate-400 italic">
                Clustered by invariant physical barrier mechanism
              </span>
            </div>
          )}
          <SifPanel sif={result.event.sif} />
        </div>
      )}
    </div>
  );
}