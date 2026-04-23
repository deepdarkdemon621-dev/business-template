import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";
import { Button } from "@/components/ui/button";
import type { PageQuery } from "@/lib/pagination";
import { problemMessage } from "@/lib/problem-details";
import { listRoles, deleteRole } from "./api";
import type { RoleListItem } from "./types";
import { DeleteRoleDialog } from "./components/DeleteRoleDialog";

const columns: ColumnDef<RoleListItem>[] = [
  {
    key: "code",
    header: "Code",
    render: (row) => <span className="font-mono">{row.code}</span>,
  },
  {
    key: "name",
    header: "Name",
    render: (row) => row.name,
  },
  {
    key: "type",
    header: "Type",
    render: (row) => {
      if (row.isSuperadmin) return <span className="rounded bg-muted px-1.5 py-0.5 text-xs">System</span>;
      if (row.isBuiltin) return <span className="rounded bg-muted px-1.5 py-0.5 text-xs">Builtin</span>;
      return null;
    },
  },
  {
    key: "userCount",
    header: "# Users",
    render: (row) => row.userCount,
  },
  {
    key: "permissionCount",
    header: "# Perms",
    render: (row) => row.permissionCount,
  },
  {
    key: "updatedAt",
    header: "Updated",
    render: (row) => new Date(row.updatedAt).toLocaleDateString(),
  },
];

export function RoleListPage() {
  const [toDelete, setToDelete] = useState<RoleListItem | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const fetcher = useCallback((pq: PageQuery) => listRoles(pq), []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Roles</h1>
        <Button asChild>
          <Link to="/admin/roles/new">+ New role</Link>
        </Button>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <DataTable<RoleListItem>
        columns={columns}
        fetcher={fetcher}
        queryKey={["roles", reloadToken]}
        rowActions={(row) => (
          <div className="flex items-center gap-1">
            <Button asChild variant="ghost" size="sm">
              <Link to={`/admin/roles/${row.id}`}>Edit</Link>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={row.isBuiltin || row.isSuperadmin}
              onClick={() => setToDelete(row)}
            >
              Delete
            </Button>
          </div>
        )}
      />

      {toDelete ? (
        <DeleteRoleDialog
          open
          roleCode={toDelete.code}
          roleName={toDelete.name}
          userCount={toDelete.userCount}
          onCancel={() => setToDelete(null)}
          onConfirm={async () => {
            try {
              await deleteRole(toDelete.id);
              setToDelete(null);
              setReloadToken((n) => n + 1);
            } catch (err) {
              setError(problemMessage(err));
            }
          }}
        />
      ) : null}
    </div>
  );
}
