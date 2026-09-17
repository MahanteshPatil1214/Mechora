const base = "/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      /* surface raw status text */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  analyze: (payload) =>
    request("/analyze", { method: "POST", body: JSON.stringify(payload) }),
  observations: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== "" && v != null),
      ),
    ).toString();
    return request(`/observations${qs ? `?${qs}` : ""}`);
  },
  families: (recurringOnly = false) =>
    request(`/families?recurring_only=${recurringOnly}`),
  dashboard: () => request("/dashboard"),
  ontology: () => request("/ontology"),
  evaluation: () => request("/evaluation/latest"),
  aggregates: (kind) => request(`/aggregates/${kind}`),
};

export const STATE_COLORS = {
  verified: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  not_verified: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  failed: "bg-rose-600/20 text-rose-200 border-rose-500/50",
  absent: "bg-orange-500/15 text-orange-300 border-orange-500/40",
  partially_effective: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  unknown: "bg-slate-500/15 text-slate-300 border-slate-500/40",
};

export const SIF_COLORS = {
  high: "bg-red-500/20 text-red-200 border-red-500/50",
  medium: "bg-amber-500/15 text-amber-200 border-amber-500/40",
  low: "bg-emerald-500/15 text-emerald-200 border-emerald-500/40",
  needs_review: "bg-sky-500/15 text-sky-200 border-sky-500/40",
};

export function label(value) {
  return (value || "unknown").replace(/_/g, " ");
}