import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import { client } from "@/api/client";
import { useAuth } from "@/lib/auth";
import type { Scope } from "./scope";

export interface PermissionsContextValue {
  isSuperadmin: boolean;
  permissions: Record<string, Scope>;
  isLoading: boolean;
  refetch: () => Promise<void>;
}

export const PermissionsContext =
  createContext<PermissionsContextValue | null>(null);

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [permissions, setPermissions] = useState<Record<string, Scope>>({});
  const [isLoading, setIsLoading] = useState(false);
  const lastFetchRef = useRef<number>(0);

  const refetch = useCallback(async () => {
    if (!user) {
      setPermissions({});
      setIsSuperadmin(false);
      return;
    }
    const now = Date.now();
    if (now - lastFetchRef.current < 500) return;
    lastFetchRef.current = now;
    setIsLoading(true);
    try {
      const { data } = await client.get<{
        isSuperadmin: boolean;
        permissions: Record<string, Scope>;
      }>("/me/permissions");
      setIsSuperadmin(data.isSuperadmin);
      setPermissions(data.permissions);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (user) void refetch();
    else {
      setPermissions({});
      setIsSuperadmin(false);
    }
  }, [user, refetch]);

  useEffect(() => {
    if (!user) return;
    const onFocus = () => void refetch();
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refetch();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [user, refetch]);

  const location = useLocation();
  useEffect(() => {
    if (user) void refetch();
  }, [location.pathname, user, refetch]);

  const value = useMemo<PermissionsContextValue>(
    () => ({ isSuperadmin, permissions, isLoading, refetch }),
    [isSuperadmin, permissions, isLoading, refetch],
  );

  return (
    <PermissionsContext.Provider value={value}>
      {children}
    </PermissionsContext.Provider>
  );
}
