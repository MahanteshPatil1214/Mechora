import React, { useState, useEffect } from "react";
import { User, Settings as SettingsIcon, Shield, Sliders, LogOut, CheckCircle2, Flame, Info, Check } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { api } from "../api.js";
import { PageHeader } from "../components/common/PageHeader.jsx";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Enterprise Page Header */}
      <PageHeader
        title="HSE Application & System Configuration"
        subtitle="Account credentials, prototype engine parameters, and active safety intelligence pipeline settings."
        breadcrumbs={[{ label: "Settings & System" }]}
      />

      {/* Account Profile Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500 font-mono font-bold text-slate-950 text-base">
              {user?.initials || "HB"}
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">{user?.name}</h2>
              <p className="text-xs text-slate-400 font-mono">{user?.email}</p>
            </div>
          </div>
          <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-xs font-semibold text-emerald-300">
            Active HSE Session
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-500 block">Organization</span>
            <span className="text-slate-200 font-semibold">{user?.organization || "Oil India Limited (OIL)"}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-500 block">Designated Role</span>
            <span className="text-slate-200 font-semibold">{user?.role || "Safety Analyst / SIH Evaluator"}</span>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800 flex justify-end">
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-medium text-rose-300 hover:border-rose-500/50 hover:bg-rose-500/10 transition-colors"
          >
            <LogOut size={14} />
            <span>Sign Out of HSE Workspace</span>
          </button>
        </div>
      </div>

      {/* Engine & Prototype Configuration Parameters */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Sliders size={16} className="text-amber-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-white">
              Structural Precursor Parameters (Backend Verified)
            </h2>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">app/config.py</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold">
              Family Assignment Threshold
            </span>
            <div className="mt-1 font-mono text-sm font-bold text-amber-400">0.65</div>
            <p className="mt-1 text-[11px] text-slate-400">
              Minimum pairwise structural similarity required to merge into a precursor family.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold">
              Recurring Precursor Threshold
            </span>
            <div className="mt-1 font-mono text-sm font-bold text-rose-400">≥ 2 observations</div>
            <p className="mt-1 text-[11px] text-slate-400">
              Observations required to trigger the recurring precursor flag.
            </p>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold">
              Structural Weights Configuration
            </span>
            <div className="mt-1 text-[11px] text-slate-300 font-mono space-y-0.5">
              <div>Barrier (20%) + State (10%) = 30%</div>
              <div>Energy / Hazard: 25%</div>
              <div>Exposure Mechanism: 20%</div>
              <div>Task Phase: 15% · Activity: 10%</div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold">
              Hard Negation Separation Rule
            </span>
            <div className="mt-1 text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
              <Check size={13} />
              <span>Strictly Enforced</span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Verified compliance observations can never merge into Not Verified failure families.
            </p>
          </div>
        </div>
      </div>

      {/* Backend & Deployment Status */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-3 text-xs">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <Flame size={15} className="text-amber-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-white">
            System Environment & API Status
          </h2>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Active Provider</span>
            <p className="font-bold text-slate-200 capitalize mt-0.5">{health?.provider || "rules (deterministic)"}</p>
          </div>
          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Data Store</span>
            <p className="font-bold text-slate-200 mt-0.5">{health?.backend || "SQLite fallback / Postgres"}</p>
          </div>
          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Version</span>
            <p className="font-bold text-slate-200 mt-0.5">{health?.version || "0.1.0 MVP"}</p>
          </div>
          <div className="rounded-lg bg-slate-950 p-3 border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-bold block">Problem Statement</span>
            <p className="font-bold text-amber-400 mt-0.5 font-mono">SIH26165</p>
          </div>
        </div>

        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 mt-2 flex items-start gap-2">
          <Info size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
          <span>
            Prototype HSE Attention Signal is an engineering decision-support tool. Production thresholds
            require official calibration with Oil India Limited historical safety incident data.
          </span>
        </div>
      </div>
    </div>
  );
}
