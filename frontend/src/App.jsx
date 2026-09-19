import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";

// Layouts
import PublicLayout from "./layouts/PublicLayout.jsx";
import HSELayout from "./layouts/HSELayout.jsx";

// Pages
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Overview from "./pages/Overview.jsx";
import Analyze from "./pages/Analyze.jsx";
import Observations from "./pages/Observations.jsx";
import ObservationDetail from "./pages/ObservationDetail.jsx";
import PrecursorFamilies from "./pages/PrecursorFamilies.jsx";
import PrecursorFamilyDetail from "./pages/PrecursorFamilyDetail.jsx";
import HSEReview from "./pages/HSEReview.jsx";
import Analytics from "./pages/Analytics.jsx";
import SettingsPage from "./pages/Settings.jsx";

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-xs">
        Authenticating HSE Session…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return children;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
        <Routes>
          {/* Public Product Pages */}
          <Route element={<PublicLayout />}>
            <Route path="/" element={<Home />} />
          </Route>

          {/* Dedicated Login */}
          <Route path="/login" element={<Login />} />

          {/* Protected HSE Workspace Pages */}
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <HSELayout />
              </ProtectedRoute>
            }
          >
            {/* Overview / Command Center */}
            <Route index element={<Overview />} />

            {/* Conversational Safety Analysis Workspace */}
            <Route path="analyze" element={<Analyze />} />

            {/* Observations Browser & Detail */}
            <Route path="observations" element={<Observations />} />
            <Route path="observations/:id" element={<ObservationDetail />} />

            {/* Precursor Families & Hero Screen Detail */}
            <Route path="families" element={<PrecursorFamilies />} />
            <Route path="families/:id" element={<PrecursorFamilyDetail />} />

            {/* HSE Human-in-the-loop Review Queue */}
            <Route path="review" element={<HSEReview />} />

            {/* Operational Analytics & Separated Model Benchmark */}
            <Route path="analytics" element={<Analytics />} />

            {/* System & Account Settings */}
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback to Home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}