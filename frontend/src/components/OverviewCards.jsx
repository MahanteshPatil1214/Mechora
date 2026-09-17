import { useEffect, useState } from "react";
import { api } from "../api.js";

function Card({ title, value, tint }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className={`text-3xl font-bold ${tint || "text-slate-100"}`}>{value}</div>
      <div className="mt-1 text-xs uppercase tracking-widest text-slate-500">{title}</div>
    </div>
  );
}

export default function OverviewCards() {
  const [dash, setDash] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.dashboard().then(setDash).catch((e) => setErr(e.message));
  }, []);

  if (err) {
    return (
      <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
        {err}
      </p>
    );
  }
  if (!dash) return <p className="text-sm text-slate-500">Loading dashboard…</p>;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Card title="Observations" value={dash.total_observations} />
      <Card title="SIF potential" value={dash.sif_potential_observations} tint="text-amber-300" />
      <Card title="Precursor families" value={dash.precursor_families} tint="text-sky-300" />
      <Card title="Recurring families" value={dash.recurring_precursor_families} tint="text-rose-300" />
    </div>
  );
}