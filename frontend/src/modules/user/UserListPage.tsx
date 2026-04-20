import { useCallback } from "react";
import { Link } from "react-router-dom";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";
import { Button } from "@/components/ui/button";
import type { PageQuery } from "@/lib/pagination";
import { listUsers } from "./api";
import type { User } from "./types";

const columns: ColumnDef<User>[] = [
  { key: "email", header: "邮箱", render: (u) => u.email },
  { key: "fullName", header: "姓名", render: (u) => u.fullName },
  {
    key: "isActive",
    header: "状态",
    render: (u) => (u.isActive ? "启用" : "停用"),
  },
  {
    key: "mustChangePassword",
    header: "强制改密",
    render: (u) => (u.mustChangePassword ? "是" : "否"),
  },
];

export function UserListPage() {
  const fetcher = useCallback(
    (pq: PageQuery) => listUsers({ ...pq, is_active: true }),
    []
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">用户管理</h1>
        <Button asChild>
          <Link to="/admin/users/new">新建用户</Link>
        </Button>
      </div>
      <DataTable<User>
        columns={columns}
        fetcher={fetcher}
        queryKey={["users"]}
        rowActions={(u) => (
          <Button asChild variant="ghost" size="sm">
            <Link to={`/admin/users/${u.id}`}>编辑</Link>
          </Button>
        )}
      />
    </div>
  );
}
