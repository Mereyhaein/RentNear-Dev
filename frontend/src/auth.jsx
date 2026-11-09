import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "./api";

const TOKEN_KEY = "rentnear_token";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      if (!token) {
        setUser(null);
        setSessionError("");
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const me = await api("/api/auth/me", { token });
        if (!cancelled) {
          setUser(me);
          setSessionError("");
        }
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
          setSessionError("");
        } else {
          setUser(null);
          setSessionError(error.message || "Could not restore your session.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadSession();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      sessionError,
      setSession(nextToken, nextUser) {
        localStorage.setItem(TOKEN_KEY, nextToken);
        setToken(nextToken);
        setUser(nextUser);
        setSessionError("");
      },
      async logout() {
        try {
          if (token) await api("/api/auth/logout", { method: "POST", token });
        } catch {
          // Local sign-out still continues if the token is already invalid.
        }
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
        setSessionError("");
      },
    }),
    [user, token, loading, sessionError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
