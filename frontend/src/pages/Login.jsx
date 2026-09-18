import React, { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Flame, Eye, EyeOff, Lock, User, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("hse.analyst@oilindia.in");
  const [password, setPassword] = useState("mechora2026");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const redirectPath = new URLSearchParams(location.search).get("redirect") || "/app";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please provide both email/username and password.");
      return;
    }

    try {
      await login({ email: email.trim(), password });
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err.message || "Authentication failed. Please verify your HSE credentials.");
    }
  };

  const handleUseDemo = () => {
    setEmail("hse.analyst@oilindia.in");
    setPassword("mechora2026");
    setError("");
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2.5">
        <Link to="/" className="inline-flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500 text-slate-950 font-bold">
            <Flame className="h-5 w-5" />
          </div>
        </Link>
        <h1 className="text-xl font-bold tracking-tight text-white">
          MECHORA <span className="text-amber-400">HSE Workspace</span>
        </h1>
        <p className="text-xs text-slate-400">
          Oil India Limited · Problem Statement SIH26165
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 sm:p-7 space-y-5 shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3.5">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-white">HSE Analyst Authentication</h2>
              <p className="text-[11px] text-slate-400">Authorized OIL Safety Personnel & Evaluators</p>
            </div>
            <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 flex items-center gap-1">
              <ShieldCheck size={12} />
              Secure
            </span>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-200 flex items-start gap-2">
              <AlertCircle size={15} className="text-rose-400 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                Work Email or Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@oilindia.in"
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-3 text-xs text-white placeholder-slate-600 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Password
                </label>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-9 pr-9 text-xs text-white placeholder-slate-600 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-white"
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-amber-500 py-2.5 text-xs font-bold text-slate-950 hover:bg-amber-400 disabled:opacity-50 transition-colors shadow-sm"
            >
              {loading ? (
                <span>Authenticating HSE Session...</span>
              ) : (
                <>
                  <span>Sign In to HSE Command Center</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials helper */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-center">
            <div className="text-[11px] text-slate-400">
              Evaluation & Demonstration Mode
            </div>
            <button
              type="button"
              onClick={handleUseDemo}
              className="mt-1 text-xs font-semibold text-amber-400 hover:text-amber-300 underline underline-offset-2"
            >
              Auto-Fill SIH Demo Credentials
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-slate-500 space-y-1">
          <p>Oil India Limited · Smart India Hackathon 2026</p>
          <p className="italic text-[11px] text-slate-500">
            Prototype HSE Attention Signal — decision support, not an official OIL risk score.
          </p>
        </div>
      </div>
    </div>
  );
}
