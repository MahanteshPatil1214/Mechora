import { STATE_COLORS, SIF_COLORS, label } from "../api.js";

export function StateBadge({ value }) {
  const cls = STATE_COLORS[value] || STATE_COLORS.unknown;
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label(value)}
    </span>
  );
}

export function FamilyTypeBadge({ type }) {
  const t = (type || "precursor").toLowerCase();
  if (t === "controlled") {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/50 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-300">
        <span>✓</span>
        <span>CONTROLLED</span>
      </span>
    );
  }
  if (t === "needs_review") {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/50 bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
        <span>⚠</span>
        <span>NEEDS REVIEW</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-rose-500/50 bg-rose-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-rose-300">
      <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
      <span>PRECURSOR</span>
    </span>
  );
}

export function SIFBadge({ value }) {
  const v = (value || "").toLowerCase();
  let labelText = "REVIEW";
  let cls = SIF_COLORS.needs_review;

  if (v === "high" || v === "yes") {
    labelText = "SIF: YES";
    cls = SIF_COLORS.high;
  } else if (v === "low" || v === "no") {
    labelText = "SIF: NO";
    cls = "border-slate-700 bg-slate-800 text-slate-300";
  } else {
    labelText = "SIF: REVIEW";
    cls = SIF_COLORS.needs_review;
  }

  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-bold tracking-wide ${cls}`}>
      {labelText}
    </span>
  );
}

export function NeedsReviewBadge({ missingFields }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 text-xs font-semibold text-amber-300">
      <span>⚠ NEEDS REVIEW</span>
      {missingFields?.length > 0 && (
        <span className="text-[10px] text-amber-400/90 font-normal">
          (missing: {missingFields.map(label).join(", ")})
        </span>
      )}
    </span>
  );
}

export function Field({ name, value, evidence, isCanonical = true, basis, basisDetail }) {
  const isUnknown = !value || value === "unknown" || value === "unknown_code";
  const isPotential = name.toLowerCase().includes("potential");
  const isActual = name.toLowerCase().includes("actual");
  const displayValue = isUnknown
    ? (isPotential ? "Unknown / Needs Review"
       : isActual ? "Unknown — not stated in report"
       : "Unknown")
    : (isActual && value === "none_identified" ? "No injury" : label(value));

  const isInferred = basis === "inferred" || basis === "model_inference"
    || (!isUnknown && !evidence && basis !== "explicit");
  const isExplicit = basis === "explicit" || (!isUnknown && !!evidence && basis !== "inferred" && basis !== "model_inference");

  return (
    <div className="flex flex-col gap-1 rounded-md border border-slate-800/80 bg-slate-900/60 p-2 min-w-[140px]">
      <div className="flex items-center justify-between gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          {name}
        </span>
        {isCanonical && (
          <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-500 lowercase">
            canonical
          </span>
        )}
      </div>
      <span
        className={`text-sm font-medium leading-snug ${
          isUnknown ? "italic text-slate-500" : "text-slate-100"
        }`}
      >
        {displayValue}
      </span>
      {!isUnknown && isInferred && !isExplicit ? (
        <div className="flex items-center gap-1">
          <span className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-300">
            {basis === "model_inference" ? "MODEL/RULE INFERENCE" : "INFERRED"}
          </span>
          <span className="text-[9px] text-amber-500/70 italic">
            {basis === "model_inference" ? "model rule, not stated in report" : "no direct span — derived"}
          </span>
        </div>
      ) : !isUnknown && isExplicit ? (
        <div className="flex items-center gap-1">
          <span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-300">
            EXPLICIT
          </span>
          <span className="text-[9px] text-emerald-500/70 italic">stated in report</span>
        </div>
      ) : null}
      {basisDetail && !isUnknown ? (
        <div className="flex items-start gap-1 text-[9px] text-amber-400/80 italic">
          <span className="not-italic font-semibold uppercase tracking-wide text-amber-500/70">basis:</span>
          <span className="break-words">{basisDetail}</span>
        </div>
      ) : null}
      {evidence ? (
        <div className="mt-0.5 flex items-start gap-1 text-[11px] text-sky-400 font-mono italic leading-tight">
          <span className="text-[10px] font-sans font-semibold uppercase tracking-tight text-sky-500/80 not-italic">
            evidence:
          </span>
          <span className="break-words">"{evidence}"</span>
        </div>
      ) : !isUnknown ? (
        <span className="text-[10px] text-slate-600 italic">no direct span</span>
      ) : null}
    </div>
  );
}

export function SifPanel({ sif }) {
  if (!sif) return null;
  const conf = Number(sif.confidence ?? 0).toFixed(2);
  const isYes = sif.classification === "high" || sif.classification === "yes";
  const basisText =
    sif.basis === "explicit"
      ? "basis: explicit narrative evidence"
      : sif.basis === "needs_review"
        ? "basis: needs HSE review"
        : "basis: rule-based inference";

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold">
            SIF Potential Assessment
          </span>
          <span className="text-[9px] rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.2 font-mono text-slate-400">
            Decision Support
          </span>
        </div>
        <div className="flex items-center gap-2">
          <SIFBadge value={sif.classification} />
          <span className="text-xs font-mono text-slate-400">confidence {conf}</span>
        </div>
      </div>

      <div>
        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
          Safety Rationale:
        </span>
        <p className="mt-0.5 text-xs text-slate-300 leading-relaxed">{sif.reason}</p>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="rounded border border-slate-600/70 bg-slate-800/70 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-300">
          {basisText}
        </span>
        {isYes && sif.basis === "rule_inference" && (
          <span className="text-[9px] italic text-amber-400/80">
            model rule, not an explicit statement — verify with HSE
          </span>
        )}
      </div>

      {sif.supporting_evidence?.length ? (
        <div className="rounded-md border border-slate-800 bg-slate-900/60 p-2 space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
            Supporting Basis & Safety Rule Matches:
          </span>
          <ul className="space-y-1 pt-0.5">
            {sif.supporting_evidence.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[11px] text-slate-300">
                <span className="text-sky-400 font-bold">•</span>
                <span>{e}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {sif.model_note ? (
        <p className="text-[10px] italic text-slate-500">{sif.model_note}</p>
      ) : null}

      <p className="text-[9px] italic text-slate-500">
        Decision-support classification for prioritizing human HSE review. Not an automated fatality prediction or official corporate risk score.
      </p>
    </div>
  );
}

export function EvidenceChips({ fieldEvidence }) {
  if (!fieldEvidence) return null;
  const entries = Object.entries(fieldEvidence).filter(([, v]) => v);
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([k, v]) => (
        <span
          key={k}
          className="rounded-md border border-slate-700/70 bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-400"
        >
          <span className="font-semibold text-slate-500">{k.replace(/_/g, " ")}:</span> “{v}”
        </span>
      ))}
    </div>
  );
}