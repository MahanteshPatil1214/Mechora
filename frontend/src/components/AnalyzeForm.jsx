import { useState } from "react";
import { api } from "../api.js";
import { Field, StateBadge, SIFBadge } from "./Badge.jsx";

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
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {result.report_id} · {result.id} · provider={result.provider}
            </span>
            <SIFBadge value={result.event.sif.classification} />
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Field name="Activity" value={result.event.activity} />
            <Field name="Task phase" value={result.event.task_phase} />
            <Field name="Energy" value={result.event.energy} />
            <Field name="Barrier" value={result.event.barrier} />
            <Field name="Exposure" value={result.event.exposure} />
            <Field name="Consequence" value={result.event.potential_consequence} />
            <Field name="Location" value={result.event.location} />
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] uppercase tracking-widest text-slate-500">Barrier state</span>
              <StateBadge value={result.event.barrier_state} />
            </div>
          </div>
          <div className="text-xs text-slate-400">
            Life-saving rules:{" "}
            {result.event.life_saving_rules?.map((r) => (
              <code key={r} className="mr-1">{r}</code>
            ))}
          </div>
          {result.event.sif?.model_note ? (
            <p className="text-[11px] italic text-slate-500">
              {result.event.sif.model_note}
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}