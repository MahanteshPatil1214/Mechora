import { useEffect, useState } from "react";
import { api } from "./api.js";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import OverviewCards from "./components/OverviewCards.jsx";
import Observations from "./components/Observations.jsx";
import FamiliesPanel from "./components/FamiliesPanel.jsx";
import EvalPanel from "./components/EvalPanel.jsx";

export default function App() {
  const [health, setHealth] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            MECHORA <span className="font-normal text-slate-400">· Prototype Precursor Attention Signal</span>
          </h1>
          <p className="text-xs text-slate-500">
            Deterministic HSE precursor engine — decision support, not a risk score
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className={`h-2 w-2 rounded-full ${health ? "bg-emerald-400" : "bg-slate-600"}`} />
          <span>backend {health?.backend ?? "…"}</span>
          <span className="text-slate-600">|</span>
          <span>provider {health?.provider ?? "…"}</span>
        </div>
      </header>

      <main className="mt-6 space-y-4">
        <AnalyzeForm onAnalyzed={() => setRefreshKey((k) => k + 1)} />
        <OverviewCards />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Observations refreshKey={refreshKey} />
          <div className="space-y-4">
            <FamiliesPanel />
          </div>
        </div>
        <EvalPanel />
      </main>
    </div>
  );
}