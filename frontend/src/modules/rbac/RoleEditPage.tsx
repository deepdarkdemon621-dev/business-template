import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FormRenderer } from "@/components/form/FormRenderer";
import { Button } from "@/components/ui/button";
import { isProblemDetails, problemMessage } from "@/lib/problem-details";
import { createRole, getRole, listPermissions, updateRole } from "./api";
import { RolePermissionMatrix } from "./components/RolePermissionMatrix";
import { roleCreateSchema, roleUpdateSchema } from "./schema";
import type { Permission, RoleDetail, RolePermissionItem } from "./types";

type RoleFormValues = {
  code: string;
  name: string;
  [key: string]: unknown;
};

export function RoleEditPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [role, setRole] = useState<RoleDetail | null>(null);
  const [allPerms, setAllPerms] = useState<Permission[]>([]);
  const [matrix, setMatrix] = useState<RolePermissionItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(isEdit);

  // Load all permissions (once).
  useEffect(() => {
    let active = true;
    listPermissions()
      .then((perms) => {
        if (active) setAllPerms(perms);
      })
      .catch((err) => {
        if (active) setError(problemMessage(err));
      });
    return () => {
      active = false;
    };
  }, []);

  // Load existing role in edit mode.
  useEffect(() => {
    if (!isEdit || !id) return;
    let active = true;
    getRole(id)
      .then((r) => {
        if (!active) return;
        setRole(r);
        setMatrix(r.permissions);
        setLoading(false);
      })
      .catch((err) => {
        if (active) {
          setError(problemMessage(err));
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [id, isEdit]);

  if (loading) {
    return <div className="p-6">Loading…</div>;
  }

  // Superadmin — fully immutable read-only view.
  if (role?.isSuperadmin) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <h1 className="text-xl font-semibold">Role: {role.name}</h1>
        <div className="rounded border border-border bg-muted/30 p-4 text-sm">
          This role is <strong>immutable</strong>. Its metadata and permissions cannot be changed.
        </div>
        <div>
          <h2 className="mb-2 text-sm font-medium">Permissions</h2>
          <RolePermissionMatrix
            value={role.permissions}
            onChange={() => {}}
            allPermissions={allPerms}
            disabled
          />
        </div>
        <Button variant="ghost" onClick={() => navigate("/admin/roles")}>
          Back
        </Button>
      </div>
    );
  }

  const schema = isEdit ? roleUpdateSchema : roleCreateSchema;
  const defaultValues: Partial<RoleFormValues> = role
    ? { code: role.code, name: role.name }
    : { code: "", name: "" };

  async function handleSubmit(
    values: RoleFormValues,
    helpers: { setFieldErrors: (e: Record<string, string>) => void },
  ) {
    setError(null);
    try {
      if (isEdit && id) {
        await updateRole(id, {
          code: values.code,
          name: values.name,
          permissions: matrix,
        });
      } else {
        await createRole({
          code: values.code ?? "",
          name: values.name ?? "",
          permissions: matrix,
        });
      }
      navigate("/admin/roles");
    } catch (err: unknown) {
      // The axios interceptor in @/api/client unwraps RFC-9457 Problem Details
      // and rejects with the ProblemDetails object directly — not an AxiosError.
      if (isProblemDetails(err)) {
        if (err.code === "role.builtin-locked") {
          helpers.setFieldErrors({
            code: "This role is built-in; code cannot be changed.",
            name: "This role is built-in; name cannot be changed.",
          });
          return;
        }
        if (err.code === "role.code-conflict") {
          helpers.setFieldErrors({ code: err.detail });
          return;
        }
        const fieldErrs: Record<string, string> = {};
        for (const e of err.errors ?? []) {
          fieldErrs[e.field] = e.message ?? e.code;
        }
        if (Object.keys(fieldErrs).length > 0) {
          helpers.setFieldErrors(fieldErrs);
          return;
        }
        setError(err.detail);
        return;
      }
      setError(problemMessage(err));
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">
        {isEdit ? `Edit role: ${role?.name ?? ""}` : "New role"}
      </h1>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <section className="rounded border border-border p-4">
        <h2 className="mb-3 text-sm font-medium">Metadata</h2>
        <FormRenderer<RoleFormValues>
          schema={schema}
          defaultValues={defaultValues}
          onSubmit={handleSubmit}
        >
          <section className="rounded border border-border p-4">
            <h2 className="mb-3 text-sm font-medium">Permissions</h2>
            <RolePermissionMatrix
              value={matrix}
              onChange={setMatrix}
              allPermissions={allPerms}
            />
          </section>
          <div className="flex gap-2">
            <Button type="submit">Save</Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/admin/roles")}>
              Cancel
            </Button>
          </div>
        </FormRenderer>
      </section>
    </div>
  );
}
