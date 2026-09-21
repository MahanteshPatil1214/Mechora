import React, { useState, useEffect } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquareCode,
  FileText,
  Network,
  ClipboardCheck,
  ShieldAlert,
  BarChart3,
  Settings,
  Search,
  Bell,
  LogOut,
  ChevronDown,
  Menu,
  X,
  ExternalLink,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Sun,
  Moon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import { api } from "../api.js";

export default function HSELayout() {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [health, setHealth] = useState(null);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {});
    api
      .observations({ limit: 100 })
      .then((res) => {
        const needsReview = (res.observations || []).filter(
          (o) =>
            o.validation === "pending" ||
            o.event?.sif?.classification === "needs_review" ||
            o.event?.evidence_status === "needs_review",
        );
        setPendingReviewCount(needsReview.length);
      })
      .catch(() => {});
  }, [location.pathname]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/app/observations?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const navGroups = [
    {
      label: "HSE Workspace",
      items: [
        {
          to: "/app",
          label: "Overview",
          icon: LayoutDashboard,
          end: true,
        },
        {
          to: "/app/analyze",
          label: "Analyze",
          icon: FileText,
        },
      ],
    },
    {
      label: "Safety Intelligence",
      items: [
        {
          to: "/app/observations",
          label: "Observations",
          icon: Search,
        },
        {
          to: "/app/families",
          label: "Precursor Families",
          icon: Network,
        },
        {
          to: "/app/analytics",
          label: "Analytics",
          icon: BarChart3,
        },
      ],
    },
    {
      label: "Corrective Action",
      items: [
        {
          to: "/app/capas",
          label: "CAPA Effectiveness",
          icon: ClipboardCheck,
        },
      ],
    },
    {
      label: "Governance",
      items: [
        {
          to: "/app/review",
          label: "HSE Review",
          icon: ShieldAlert,
          badge: pendingReviewCount > 0 ? pendingReviewCount : null,
        },
      ],
    },
    {
      label: "System",
      items: [
        {
          to: "/app/settings",
          label: "Settings",
          icon: Settings,
        },
      ],
    },
  ];

  return (
    <div className="h-screen h-[100dvh] bg-slate-950 text-slate-100 flex flex-col font-sans overflow-hidden">
      {/* Top Bar - Fixed height, persistent */}
      <header className="h-14 flex-shrink-0 z-30 flex items-center justify-between border-b border-slate-800 bg-slate-950 px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-white lg:hidden"
            aria-label="Toggle sidebar"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>

          <Link to="/app" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-600 text-slate-950 font-black">
              <Flame className="h-4.5 w-4.5 text-slate-950" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 leading-none">
                <span className="text-sm font-bold tracking-tight text-white">MECHORA</span>
                <span className="hidden sm:inline-block rounded bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-amber-300 border border-amber-500/20">
                  SIH26165
                </span>
              </div>
              <span className="hidden sm:block text-[10px] font-medium text-slate-400 mt-0.5">
                Structural Precursor Intelligence
              </span>
            </div>
          </Link>
        </div>

        {/* Center Search Input */}
        <form
          onSubmit={handleSearchSubmit}
          className="hidden md:flex flex-1 max-w-md mx-6 relative items-center"
        >
          <Search className="absolute left-3.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search observations, precursors, barriers... (Press Enter)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-slate-800 bg-slate-900 py-1 pl-9 pr-12 text-xs text-slate-200 placeholder-slate-500 focus:border-amber-500 focus:bg-slate-900 focus:outline-none transition-colors"
          />
          <kbd className="absolute right-2.5 rounded border border-slate-700 bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-400">
            ↵
          </kbd>
        </form>

        {/* Right Status & User Menu */}
        <div className="flex items-center gap-2.5">
          {/* Dark / Light Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-300 hover:border-slate-700 hover:text-white transition-colors"
            title={isDark ? "Switch to light theme" : "Switch to dark theme"}
            aria-label="Toggle color theme"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* AI Engine Status Pill */}
          <div className="hidden sm:flex items-center gap-1.5 rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[11px] text-emerald-300 font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span>Engine Online</span>
          </div>

          {/* Notifications / Review Indicator */}
          <Link
            to="/app/review"
            className="relative rounded-lg border border-slate-800 bg-slate-900 p-1.5 text-slate-300 hover:border-slate-700 hover:text-white transition-colors"
            title={
              pendingReviewCount > 0
                ? `${pendingReviewCount} observations require HSE review`
                : "HSE Review Queue"
            }
          >
            <Bell size={16} />
            {pendingReviewCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white shadow-sm">
                {pendingReviewCount}
              </span>
            )}
          </Link>

          {/* User Profile Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 hover:border-slate-700 hover:bg-slate-850 transition-all text-left"
            >
              <div className="flex h-6 w-6 items-center justify-center rounded bg-amber-600 font-mono text-[10px] font-bold text-slate-950">
                {user?.initials || "HB"}
              </div>
              <div className="hidden lg:block">
                <div className="text-xs font-semibold text-slate-200 leading-tight">{user?.name || "HSE Analyst"}</div>
              </div>
              <ChevronDown size={12} className="text-slate-400" />
            </button>

            {userMenuOpen && (
              <div
                className="absolute right-0 mt-2 w-56 rounded-lg border border-slate-800 bg-slate-900 p-1.5 shadow-xl shadow-black/80 z-50"
                onClick={() => setUserMenuOpen(false)}
              >
                <div className="border-b border-slate-800 px-3 py-2">
                  <p className="text-xs font-bold text-white">{user?.name}</p>
                  <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
                  <span className="mt-1 inline-block rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-300 border border-amber-500/30">
                    {user?.role || "HSE Safety Lead"}
                  </span>
                </div>
                <div className="py-1">
                  <Link
                    to="/app/settings"
                    className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
                  >
                    <Settings size={13} />
                    Settings & System Health
                  </Link>
                  <Link
                    to="/"
                    className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
                  >
                    <ExternalLink size={13} />
                    Overview Landing Page
                  </Link>
                </div>
                <div className="border-t border-slate-800 pt-1">
                  <button
                    type="button"
                    onClick={logout}
                    className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-xs font-medium text-rose-400 hover:bg-rose-500/10"
                  >
                    <LogOut size={13} />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Workspace Body - takes full remaining height */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Mobile backdrop */}
        {mobileOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Left Sidebar - Persistent full-height on desktop, drawer on mobile */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-56 border-r border-slate-800 bg-slate-950 px-2.5 py-4 transition-transform duration-200 lg:static lg:translate-x-0 lg:z-auto lg:h-full lg:flex-shrink-0 flex flex-col justify-between overflow-y-auto ${
            mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
          }`}
        >
          <div className="space-y-3">
            {navGroups.map((group) => (
              <div key={group.label}>
                <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {group.label}
                </div>
                <nav className="space-y-0.5">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.end}
                        onClick={() => setMobileOpen(false)}
                        className={({ isActive }) =>
                          `flex items-center justify-between rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                            isActive
                              ? "bg-slate-900 text-amber-400 font-semibold border border-slate-800"
                              : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                          }`
                        }
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon size={15} />
                          <span>{item.label}</span>
                        </div>
                        {item.badge != null && (
                          <span className="rounded bg-rose-500/20 px-1.5 py-0.2 text-[10px] font-bold text-rose-300">
                            {item.badge}
                          </span>
                        )}
                      </NavLink>
                    );
                  })}
                </nav>
              </div>
            ))}
          </div>

          {/* Simple Bottom Workspace Note */}
          <div className="px-3 py-2 text-[11px] text-slate-400 border-t border-slate-800">
            <span className="text-slate-300 font-medium block">Oil India Limited</span>
            <span className="text-slate-400 font-mono text-[10px]">PS SIH26165</span>
          </div>
        </aside>

        {/* Scrollable Main Content Area with its own vertical scrolling */}
        <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto">
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
            <Outlet />
          </main>

          {/* Global Prototype Disclaimer Footer at bottom of scrollable content */}
          <footer className="mt-auto border-t border-slate-800 bg-slate-950 px-4 py-2.5 text-center text-xs text-slate-400 flex flex-wrap items-center justify-between gap-2 flex-shrink-0">
            <div className="flex items-center gap-2 text-[11px]">
              <span className="font-semibold text-slate-300">MECHORA</span>
              <span>·</span>
              <span>Oil India Limited</span>
              <span>·</span>
              <span>PS SIH26165</span>
            </div>
            <div className="italic text-[11px] text-slate-400">
              Prototype HSE Attention Signal — decision support, not an official OIL risk score or accident prediction.
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
