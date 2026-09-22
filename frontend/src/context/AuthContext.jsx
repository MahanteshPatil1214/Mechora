import React, { createContext, useContext, useState, useEffect } from "react";
import { api, getStoredUser } from "../api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Server-side session invalidation (expired/revoked token) mid-session:
    // api.js clears local auth and emits this event; we drop the user so the
    // ProtectedRoute bounces back to /login.
    const onUnauthorized = () => setUser(null);
    if (typeof window !== "undefined") {
      window.addEventListener("mechora:unauthorized", onUnauthorized);
      return () => window.removeEventListener("mechora:unauthorized", onUnauthorized);
    }
    return undefined;
  }, []);

  const login = async ({ email, password }) => {
    setLoading(true);
    try {
      const authenticatedUser = await api.login({ email, password });
      setUser(authenticatedUser);
      return authenticatedUser;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setUser(null);
    await api.logout();
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