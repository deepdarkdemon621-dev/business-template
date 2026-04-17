import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { client } from "@/api/client";
import { clearToken, setToken } from "./storage";

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  departmentId: string | null;
  isActive: boolean;
  mustChangePassword: boolean;
}

export interface AuthContextValue {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
    captcha?: string,
  ) => Promise<{ mustChangePassword: boolean }>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshToken = useCallback(async (): Promise<string | null> => {
    try {
      const { data } = await client.post<{ accessToken: string }>(
        "/auth/refresh",
      );
      setAccessToken(data.accessToken);
      setToken(data.accessToken);
      return data.accessToken;
    } catch {
      setUser(null);
      setAccessToken(null);
      clearToken();
      return null;
    }
  }, []);

  // Wire the refresh function into the axios interceptor so the 401 handler
  // can call it without a circular import.
  useEffect(() => {
    // Imported lazily to avoid circular dependency at module init time.
    import("@/api/client").then(({ setRefreshTokenFn }) => {
      if (setRefreshTokenFn) {
        setRefreshTokenFn(refreshToken);
      }
    });
    return () => {
      import("@/api/client").then(({ setRefreshTokenFn }) => {
        if (setRefreshTokenFn) {
          setRefreshTokenFn(() => Promise.resolve(null));
        }
      });
    };
  }, [refreshToken]);

  useEffect(() => {
    refreshToken().finally(() => setIsLoading(false));
  }, [refreshToken]);

  const login = useCallback(
    async (email: string, password: string, captcha?: string) => {
      const { data } = await client.post<{
        accessToken: string;
        user: AuthUser;
        mustChangePassword: boolean;
      }>("/auth/login", { email, password, captcha });
      setUser(data.user);
      setAccessToken(data.accessToken);
      setToken(data.accessToken);
      return { mustChangePassword: data.mustChangePassword };
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await client.post("/auth/logout");
    } finally {
      setUser(null);
      setAccessToken(null);
      clearToken();
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
      refreshToken,
    }),
    [user, accessToken, isLoading, login, logout, refreshToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
