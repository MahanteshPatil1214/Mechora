import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  ShieldAlert,
  AlertTriangle,
  Network,
  Repeat,
  ArrowRight,
  ChevronRight,
  ClipboardCheck,
  Plus,
  Clock,
  Radar,
  TrendingDown,
  RotateCcw,
  Eye,
  MapPin,
  Activity,
} from "lucide-react";
import {
  api,
  label,
  pickCapaSignal,
  deriveCapaPortfolio,
  deriveBarrierHealth,
  selectHighSignalObservations,
  selectTopFamilies,
  timeAgo,
} from "../api.js";
import { SIFBadge } from "../components/common/StatusBadge.jsx";
import { EffectivenessBadge } from "../components/CapaEffectiveness.jsx";
import EvidenceChain from "../components/EvidenceChain.jsx";

const TONE_DOT = {
  rose: "bg-rose-500",
  amber: "bg-amber-500",
  emerald: "bg-emerald-500",
  sky: "bg-sky-500",
  slate: "bg-slate-500",
};

const TONE_TEXT = {
  rose: "text-rose-300",
  amber: "text-amber-300",
  emerald: "text-emerald-300",
  sky: "text-sky-300",
  slate: "text-slate-200",
};

const HEALTH_BADGE = {
  Recurrence: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  Recurring: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  "Under Observation": "border-amber-500/40 bg-amber-500/10 text-amber-300",
  "Needs Review": "border-amber-500/40 bg-amber-500/10 text-amber-300",
  Stable: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
};

function SectionTitle({ icon: Icon, title, description, to, cta }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-3">
      <div className="flex items-start gap-2">
        {Icon && <Icon size={15} className="mt-0.5 text-amber-400 flex-shrink-0" />}
        <div>
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          {description && (
            <p className="mt-0.5 text-[11px] text-slate-400">{description}</p>
          )}
        </div>
      </div>
      {to && (
        <Link
          to={to}
          className="flex flex-shrink-0 items-center gap-1 text-[11px] font-medium text-amber-400 hover:text-amber-300 hover:underline"
        >
          <span>{cta}</span>
          <ChevronRight size={13} />
        </Link>
      )}
    </div>
  );
}

export default function Overview() {
  const [dashboard, setDashboard] = useState(null);
  const [observations, setObservations] = useState([]);
  const [families, setFamilies] = useState([]);
  const [capas, setCapas] = useState([]);
  const [barrierAggs, setBarrierAggs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    Promise.all([
      api.dashboard().catch(() => null),
      api.observations({ limit: 200 }).catch(() => ({ observations: [] })),
      api.families(false, 50).catch(() => ({ families: [] })),
      api.capas({ limit: 500 }).catch(() => ({ capas: [] })),
      api.aggregates("barrier").catch(() => []),
    ]).then(([dashData, obsData, famData, capaData, barrierData]) => {
      setDashboard(dashData);
      setObservations(obsData?.observations || []);
      setFamilies(famData?.families || []);
      setCapas(capaData?.capas || []);
      setBarrierAggs(Array.isArray(barrierData) ? barrierData : []);
      setLastUpdated(Date.now());
      setLoading(false);
    });
  }, []);

  const capaPortfolio = useMemo(() => deriveCapaPortfolio(capas), [capas]);

  const barrierRows = useMemo(
    () => deriveBarrierHealth(barrierAggs, families, capas),
    [barrierAggs, families, capas],
  );

  const highSignal = useMemo(
    () => selectHighSignalObservations(observations, 4),
    [observations],
  );

  const topFamilies = useMemo(() => selectTopFamilies(families, 3), [families]);

  const needsReviewCount = useMemo(
    () =>
      observations.filter(
        (o) =>
          o.validation === "pending" ||
          o.event?.sif?.classification === "needs_review" ||
          o.event?.evidence_status === "needs_review",
      ).length,
    [observations],
  );

  const criticalBarriers = barrierRows.filter((r) => r.failures > 0).length;

  const topFamily = topFamilies[0] || null;
  const topCapa = useMemo(
    () =>
      topFamily?.common_barrier
        ? pickCapaSignal(capas, [topFamily.common_barrier])
        : null,
    [capas, topFamily],
  );

  const kpis = [
    {
      key: "observations",
      label: "Observations",
      value: dashboard?.total_observations ?? 0,
      icon: FileText,
      tone: "text-slate-100",
      hint: "Records analyzed",
    },
    {
      key: "sif",
      label: "SIF Potential",
      value: dashboard?.sif_potential_observations ?? 0,
      icon: ShieldAlert,
      tone: "text-rose-300",
      hint: "High / medium",
    },
    {
      key: "failures",
      label: "Barrier Failures",
      value: dashboard?.recurring_barrier_failures ?? 0,
      icon: AlertTriangle,
      tone: "text-amber-300",
      hint: "Unverified or failed",
    },
    {
      key: "families",
      label: "Precursor Families",
      value: dashboard?.precursor_families ?? 0,
      icon: Network,
      tone: "text-sky-300",
      hint: "Mechanism clusters",
    },
    {
      key: "recurring",
      label: "Recurring Families",
      value: dashboard?.recurring_precursor_families ?? 0,
      icon: Repeat,
      tone: "text-rose-300",
      hint: "≥ 2 reports",
    },
  ];

  const safetySignals = [
    {
      key: "critical",
      label: "Critical barriers",
      hint: "Barriers with a failure state",
      value: criticalBarriers,
      tone: "rose",
    },
    {
      key: "recurring",
      label: "Recurring families",
      hint: "Cross-equipment mechanisms",
      value: dashboard?.recurring_precursor_families ?? 0,
      tone: "rose",
    },
    {
      key: "review",
      label: "Needs review",
      hint: "Human-in-the-loop pending",
      value: needsReviewCount,
      tone: "amber",
    },
  ];

  const capaSignals = [
    {
      key: "open",
      label: "Open CAPAs",
      value: capaPortfolio.open,
      tone: "sky",
      icon: ClipboardCheck,
    },
    {
      key: "under",
      label: "Under Observation",
      value: capaPortfolio.underObservation,
      tone: "amber",
      icon: Eye,
    },
    {
      key: "improvement",
      label: "Evidence of Improvement",
      value: capaPortfolio.improvementObserved,
      tone: "emerald",
      icon: TrendingDown,
    },
    {
      key: "recurrence",
      label: "Recurrence Detected",
      value: capaPortfolio.recurrenceDetected,
      tone: "rose",
      icon: RotateCcw,
    },
  ];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-400">
        Loading Safety Intelligence…
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-slate-800 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400">
            <Radar size={13} />
            <span>HSE Workspace</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
            Safety Intelligence Command Center
          </h1>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-400">
            Observation → Barrier Failure → Precursor → CAPA → Post-CAPA Evidence →
            Effectiveness → Organizational Learning.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Clock size={12} />
              Last updated {timeAgo(new Date(lastUpdated).toISOString(), now)}
            </span>
          )}
          <Link
            to="/app/analyze"
            className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-amber-500"
          >
            <Plus size={14} />
            <span>Analyze Observation</span>
          </Link>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.key}
              className="rounded-lg border border-slate-800 bg-slate-900 p-3.5"
            >
              <div className="flex items-center justify-between text-[10px] font-medium uppercase tracking-wider text-slate-400">
                <span>{kpi.label}</span>
                <Icon size={14} className="text-slate-500" />
              </div>
              <div className={`mt-1.5 font-mono text-2xl font-black leading-none ${kpi.tone}`}>
                {kpi.value}
              </div>
              <div className="mt-1 text-[10px] text-slate-500">{kpi.hint}</div>
            </div>
          );
        })}
      </div>

      {/* Signals + CAPA effectiveness */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <SectionTitle
            icon={Activity}
            title="Safety Signals"
            description="What needs attention right now."
            to="/app/families"
            cta="View attention"
          />
          <div className="mt-3 space-y-2">
            {safetySignals.map((s) => (
              <div
                key={s.key}
                className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-950 px-3 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <span className={`h-2 w-2 rounded-full ${TONE_DOT[s.tone]}`} />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{s.label}</div>
                    <div className="text-[10px] text-slate-500">{s.hint}</div>
                  </div>
                </div>
                <span className={`font-mono text-lg font-black ${TONE_TEXT[s.tone]}`}>
                  {s.value}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
            <Link
              to="/app/review"
              className="text-[11px] font-medium text-amber-400 hover:text-amber-300 hover:underline"
            >
              Review queue →
            </Link>
            <span className="text-[10px] text-slate-500">
              {dashboard?.locations_affected ?? 0} sites ·{" "}
              {dashboard?.activities_affected ?? 0} activities in scope
            </span>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <SectionTitle
            icon={ClipboardCheck}
            title="CAPA Effectiveness"
            description="What happened after we acted."
            to="/app/capas"
            cta="View CAPA Evidence"
          />
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            {capaSignals.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.key}
                  className="rounded-md border border-slate-800 bg-slate-950 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      {s.label}
                    </span>
                    <Icon size={13} className={TONE_TEXT[s.tone]} />
                  </div>
                  <div className={`mt-1.5 font-mono text-2xl font-black leading-none ${TONE_TEXT[s.tone]}`}>
                    {s.value}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
            <span className="text-[10px] text-slate-500">
              {capaPortfolio.total} CAPAs · {capaPortfolio.closed} closed
            </span>
            <Link
              to="/app/capas"
              className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 hover:text-amber-300 hover:underline"
            >
              <span>View CAPA Evidence</span>
              <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </div>

      {/* Key Attention Area */}
      {topFamily ? (
        <div className="rounded-xl border border-amber-500/30 bg-gradient-to-br from-slate-900 to-slate-950 p-5 sm:p-6">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-amber-400">
            <Radar size={12} />
            <span>Key Attention Area</span>
          </div>

          <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 space-y-2">
              <h2 className="text-lg font-bold text-white sm:text-xl">
                {topFamily.name}
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                {topCapa ? (
                  <EffectivenessBadge status={topCapa.effectiveness_status} />
                ) : topFamily.recurring ? (
                  <span className="inline-flex items-center rounded border border-rose-500/40 bg-rose-500/10 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-rose-300">
                    Recurring Barrier Breakdown
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Precursor Candidate
                  </span>
                )}
                <span className="rounded border border-slate-800 bg-slate-900 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                  {topFamily.id}
                </span>
                <span className="flex items-center gap-1 text-[11px] capitalize text-slate-300">
                  <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT.rose}`} />
                  {label(topFamily.common_barrier)}
                </span>
              </div>
              <p className="max-w-2xl text-xs leading-relaxed text-slate-300">
                {topFamily.description}
              </p>
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Evidence Chain — every step is clickable
            </div>
            <EvidenceChain family={topFamily} capa={topCapa} />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-800 pt-4">
            <Link
              to={`/app/families/${topFamily.id}`}
              className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-xs font-semibold text-slate-950 transition-colors hover:bg-amber-500"
            >
              <span>View Evidence Chain</span>
              <ArrowRight size={13} />
            </Link>
            {topCapa && (
              <Link
                to={`/app/capas/${topCapa.id}`}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-200 transition-colors hover:bg-slate-800"
              >
                <span>View CAPA</span>
                <ArrowRight size={13} />
              </Link>
            )}
            <span className="text-[11px] italic text-slate-500">
              Recurring barrier failure → CAPA → post-CAPA evidence → effectiveness verdict
            </span>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 p-6 text-center">
          <p className="text-xs font-semibold text-slate-300">
            No recurring precursor detected yet
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            Analyze observations to start identifying recurring barrier mechanisms.
          </p>
        </div>
      )}

      {/* Barrier Health */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
        <SectionTitle
          icon={Activity}
          title="Barrier Health"
          description="Deterministic signal per barrier — no black-box score."
          to="/app/families"
          cta="View Barrier Intelligence"
        />

        {barrierRows.length === 0 ? (
          <div className="mt-3 rounded-md border border-dashed border-slate-800 p-4 text-center text-[11px] text-slate-500">
            No barrier evidence yet.
          </div>
        ) : (
          <div className="mt-3 space-y-2">
            {barrierRows.slice(0, 5).map((r) => {
              const verifiedPct = r.total ? (r.verified / r.total) * 100 : 0;
              const failurePct = r.total ? (r.failures / r.total) * 100 : 0;
              return (
                <div
                  key={r.barrier}
                  className="grid grid-cols-1 items-center gap-3 rounded-md border border-slate-800 bg-slate-950 px-3 py-2.5 sm:grid-cols-[1.3fr_1.6fr_auto]"
                >
                  <div className="flex items-center gap-2">
                    <span className={`font-mono text-xs ${TONE_TEXT[r.tone]}`}>
                      {r.signal}
                    </span>
                    <span className="text-xs font-semibold capitalize text-slate-200">
                      {label(r.barrier)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="flex h-2 w-full overflow-hidden rounded-full border border-slate-700/50 bg-slate-800">
                      {r.verified > 0 && (
                        <div
                          className="h-full bg-emerald-500"
                          style={{ width: `${verifiedPct}%` }}
                        />
                      )}
                      {r.failures > 0 && (
                        <div
                          className="h-full bg-rose-500"
                          style={{ width: `${failurePct}%` }}
                        />
                      )}
                    </div>
                    <span className="w-16 flex-shrink-0 text-right font-mono text-[10px] text-slate-500">
                      {r.failures}/{r.total} fail
                    </span>
                  </div>

                  <span
                    className={`justify-self-start rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider sm:justify-self-end ${
                      HEALTH_BADGE[r.status] || HEALTH_BADGE.Stable
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent high-signal events + Top precursor families */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <SectionTitle
            icon={AlertTriangle}
            title="Recent High-Signal Events"
            description="Latest SIF-potential or failed-barrier observations."
            to="/app/observations"
            cta="View observations"
          />
          {highSignal.length === 0 ? (
            <div className="mt-3 rounded-md border border-dashed border-slate-800 p-4 text-center text-[11px] text-slate-500">
              No high-signal events logged.
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {highSignal.map((o) => (
                <Link
                  key={o.id}
                  to={`/app/observations/${o.id}`}
                  className="block rounded-md border border-slate-800 bg-slate-950 p-3 transition-colors hover:border-slate-700 hover:bg-slate-900/70"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-2">
                      <span
                        className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${
                          o.event?.sif?.classification === "high"
                            ? TONE_DOT.rose
                            : o.event?.sif?.classification === "medium"
                              ? TONE_DOT.amber
                              : TONE_DOT.sky
                        }`}
                      />
                      <div className="min-w-0">
                        <div className="truncate text-xs font-semibold capitalize text-white">
                          {label(o.event?.barrier)} {label(o.event?.barrier_state)}
                        </div>
                        <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-slate-400">
                          <span className="capitalize">
                            {label(o.event?.activity)}
                          </span>
                          {o.event?.location && o.event.location !== "unknown" && (
                            <>
                              <span>·</span>
                              <span className="inline-flex items-center gap-1 capitalize">
                                <MapPin size={10} />
                                {label(o.event.location)}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-shrink-0 flex-col items-end gap-1">
                      <SIFBadge value={o.event?.sif?.classification} />
                      <span className="text-[10px] text-slate-500">
                        {timeAgo(o.created_at, now)}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <SectionTitle
            icon={Network}
            title="Top Precursor Families"
            description="Highest attention mechanisms."
            to="/app/families"
            cta="View all"
          />
          {topFamilies.length === 0 ? (
            <div className="mt-3 rounded-md border border-dashed border-slate-800 p-4 text-center text-[11px] text-slate-500">
              No precursor families yet.
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {topFamilies.map((f) => (
                <div
                  key={f.id}
                  className="rounded-md border border-slate-800 bg-slate-950 p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Link
                      to={`/app/families/${f.id}`}
                      className="font-mono text-[11px] font-bold text-amber-400 hover:text-amber-300"
                    >
                      {f.id}
                    </Link>
                    {f.recurring && (
                      <span className="rounded border border-rose-500/30 bg-rose-500/15 px-1.5 py-0.5 text-[9px] font-bold uppercase text-rose-300">
                        Recurring
                      </span>
                    )}
                  </div>
                  <div className="mt-1 truncate text-xs font-semibold text-white">
                    {f.name}
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="capitalize">{label(f.common_barrier)}</span>
                    <span className="font-mono text-amber-300">
                      {(Number(f.attention_signal) || 0).toFixed(1)} Attention
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
            <span className="text-[10px] text-slate-500">
              {dashboard?.precursor_families ?? 0} precursor families ·{" "}
              {dashboard?.recurring_precursor_families ?? 0} recurring
            </span>
            <Link
              to="/app/families"
              className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 hover:text-amber-300 hover:underline"
            >
              <span>View all</span>
              <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
