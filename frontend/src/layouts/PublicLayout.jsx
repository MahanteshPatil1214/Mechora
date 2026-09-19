import React from "react";
import { Link, Outlet } from "react-router-dom";
import { Flame, ArrowRight, ShieldCheck, Lock, Sun, Moon } from "lucide-react";
import { useTheme } from "../context/ThemeContext.jsx";

export default function PublicLayout() {
  const { isDark, toggleTheme } = useTheme();
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-black">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/90 px-4 lg:px-8 py-3.5 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500 text-slate-950 font-bold">
              <Flame className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold tracking-tight text-white">MECHORA</span>
                <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-300 border border-amber-500/30">
                  SIH26165
                </span>
              </div>
              <span className="text-[10px] font-medium tracking-wide text-slate-400">
                Oil India Limited · Smart Automation
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-300">
            <a href="#mechanism-flow" className="hover:text-amber-400 transition-colors">
              Pipeline
            </a>
            <a href="#explainability" className="hover:text-amber-400 transition-colors">
              Explainability
            </a>
            <a href="#governance" className="hover:text-amber-400 transition-colors">
              Governance
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {/* Dark / Light Theme Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:border-slate-700 hover:text-white transition-colors"
              title={isDark ? "Switch to light theme" : "Switch to dark theme"}
              aria-label="Toggle color theme"
            >
              {isDark ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            <Link
              to="/login"
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-amber-400 transition-colors shadow-sm"
            >
              <span>HSE Workspace</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Page Outlet */}
      <div className="flex-1">
        <Outlet />
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-10 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 border-b border-slate-900 pb-8">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <Flame size={18} />
              </div>
              <div>
                <span className="font-extrabold text-white text-sm tracking-tight">MECHORA</span>
                <p className="text-xs text-slate-400">
                  Mechanism-based Operational Risk Awareness · Oil India Limited
                </p>
              </div>
            </div>

            <div className="text-center md:text-right">
              <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs text-slate-400 inline-flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-emerald-400" />
                Deterministic AI & HSE Rules · Decision Support
              </span>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
            <p>© 2026 MECHORA · PS SIH26165 · Smart India Hackathon 2026</p>
            <p className="italic text-amber-400/70 text-[11px]">
              Prototype HSE Attention Signal — decision support, not an official OIL risk score or accident prediction.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
