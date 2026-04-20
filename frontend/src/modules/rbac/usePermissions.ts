import { useContext } from "react";
import { PermissionsContext } from "./PermissionsProvider";
import { atLeast, type Scope } from "./scope";

export function usePermissions() {
  const ctx = useContext(PermissionsContext);
  if (!ctx)
    throw new Error("usePermissions must be used under PermissionsProvider");
  const { isSuperadmin, permissions, isLoading, refetch } = ctx;
  function has(code: string, minScope?: Scope): boolean {
    if (isSuperadmin) return true;
    const s = permissions[code];
    if (!s) return false;
    return minScope ? atLeast(s, minScope) : true;
  }
  return { has, isSuperadmin, permissions, isLoading, refetch };
}
