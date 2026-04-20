import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { usePermissions } from "@/modules/rbac/usePermissions";
import type { Scope } from "@/modules/rbac/scope";

interface Props {
  permission: string;
  minScope?: Scope;
  children: ReactNode;
}

export function RequirePermission({ permission, minScope, children }: Props) {
  const { has, isLoading } = usePermissions();
  if (isLoading) return null;
  if (!has(permission, minScope)) return <Navigate to="/403" replace />;
  return <>{children}</>;
}
