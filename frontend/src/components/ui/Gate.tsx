import type { ReactNode } from "react";
import { usePermissions } from "@/modules/rbac/usePermissions";
import type { Scope } from "@/modules/rbac/scope";

interface GateProps {
  permission: string;
  minScope?: Scope;
  fallback?: ReactNode;
  children: ReactNode;
}

export function Gate({
  permission,
  minScope,
  fallback = null,
  children,
}: GateProps) {
  const { has } = usePermissions();
  return <>{has(permission, minScope) ? children : fallback}</>;
}
