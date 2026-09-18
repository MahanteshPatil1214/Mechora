import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

const DEMO_USER = {
  name: "HSE Safety Analyst",
  email: "hse.analyst@oilindia.in",
  role: "HSE Field Analyst / SIH Evaluator",
  organization: "Oil India Limited (OIL)",
  initials: "HB",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("mechora_user");
      return saved ? JSON.parse(saved) : DEMO_USER;
    } catch {
      return DEMO_USER;
    }
  });

  const [loading, setLoading] = useState(false);

  const login = async ({ email, password }) => {
    setLoading(true);
    // Simulate brief network verification
    await new Promise((resolve) => setTimeout(resolve, 350));
    const authenticatedUser = {
      name: email.split("@")[0].replace(/[._]/g, " ").toUpperCase() || "HSE Analyst",
      email: email || "hse.analyst@oilindia.in",
      role: "HSE Field Specialist",
      organization: "Oil India Limited (OIL)",
      initials: (email[0] || "H").toUpperCase() + "B",
    };
    setUser(authenticatedUser);
    try {
      sessionStorage.setItem("mechora_user", JSON.stringify(authenticatedUser));
    } catch {
      /* ignore */
    }
    setLoading(false);
    return authenticatedUser;
  };

  const logout = () => {
    setUser(null);
    try {
      sessionStorage.removeItem("mechora_user");
    } catch {
      /* ignore */
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
