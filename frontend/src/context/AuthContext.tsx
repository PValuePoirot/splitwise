import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi, clearTokens, hasStoredSession, setTokens } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasStoredSession()) {
      setLoading(false);
      return;
    }
    // Try to refresh on load.
    (async () => {
      try {
        const refreshResp = await fetch(
          `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              refresh_token: localStorage.getItem("splitwise_refresh_token"),
            }),
          },
        );
        if (!refreshResp.ok) {
          clearTokens();
          setLoading(false);
          return;
        }
        const tokens = await refreshResp.json();
        setTokens(tokens.access_token, tokens.refresh_token);
        const me = await authApi.me();
        setUser(me);
      } catch {
        clearTokens();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token, refresh_token } = await authApi.login({ email, password });
    setTokens(access_token, refresh_token);
    const me = await authApi.me();
    setUser(me);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await authApi.register({ name, email, password });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
