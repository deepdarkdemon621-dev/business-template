import { usePermissions } from "@/modules/rbac/usePermissions";

export function DashboardPage() {
  const { isSuperadmin, permissions } = usePermissions();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      {import.meta.env.DEV && (
        <div className="rounded border p-4 text-sm">
          <div className="font-semibold">Your permissions (dev debug)</div>
          <div>superadmin: {String(isSuperadmin)}</div>
          <pre className="mt-2 text-xs">
            {JSON.stringify(permissions, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
