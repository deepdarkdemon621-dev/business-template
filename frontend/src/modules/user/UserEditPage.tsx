import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FormRenderer } from "@/components/form/FormRenderer";
import { Button } from "@/components/ui/button";
import { isProblemDetails, problemMessage } from "@/lib/problem-details";
import { RoleAssignmentPanel } from "./components/RoleAssignmentPanel";
import {
  assignRole,
  createUser,
  getUser,
  revokeRole,
  updateUser,
} from "./api";
import { userCreateSchema, userUpdateSchema } from "./schema";
import type { UserDetail } from "./types";

type CreateValues = {
  email: string;
  fullName: string;
  password: string;
  [key: string]: unknown;
};
type UpdateValues = {
  fullName: string;
  [key: string]: unknown;
};

export type UserEditPageProps = { mode: "create" | "edit" };

export function UserEditPage({ mode }: UserEditPageProps) {
  const nav = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [detail, setDetail] = useState<UserDetail | null>(null);
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const initialRoleIdsRef = useRef<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(mode === "edit");

  useEffect(() => {
    if (mode !== "edit" || !id) return;
    let active = true;
    getUser(id)
      .then((d) => {
        if (!active) return;
        setDetail(d);
        const rIds = d.roles.map((r) => r.id);
        setRoleIds(rIds);
        initialRoleIdsRef.current = rIds;
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
  }, [id, mode]);

  function handleProblemDetails(
    err: unknown,
    setFieldErrors: (e: Record<string, string>) => void,
  ): void {
    if (isProblemDetails(err)) {
      if (err.errors?.length) {
        setFieldErrors(
          Object.fromEntries(err.errors.map((e) => [e.field, e.message ?? e.code])),
        );
      } else {
        setError(err.detail);
      }
    } else {
      setError(problemMessage(err));
    }
  }

  if (loading) return <div className="p-6">Loading…</div>;

  if (mode === "create") {
    return (
      <div className="flex max-w-lg flex-col gap-4 p-6">
        <h1 className="text-xl font-semibold">新建用户</h1>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <FormRenderer<CreateValues>
          schema={userCreateSchema}
          defaultValues={{ email: "", fullName: "", password: "" }}
          onSubmit={async (values, { setFieldErrors }) => {
            setError(null);
            try {
              const created = await createUser({
                email: values.email,
                password: values.password,
                fullName: values.fullName,
                mustChangePassword: true,
              });
              nav(`/admin/users/${created.id}`);
            } catch (err) {
              handleProblemDetails(err, setFieldErrors);
            }
          }}
        >
          <p className="text-xs text-muted-foreground">
            至少 10 个字符，需包含字母和数字。
          </p>
          <div className="flex gap-2">
            <Button type="submit">创建</Button>
            <Button type="button" variant="ghost" onClick={() => nav(-1)}>
              取消
            </Button>
          </div>
        </FormRenderer>
      </div>
    );
  }

  // Edit mode
  return (
    <div className="flex max-w-lg flex-col gap-4 p-6">
      <h1 className="text-xl font-semibold">编辑用户</h1>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {detail ? (
        <>
          <div className="flex flex-col gap-1 text-sm">
            <span className="font-medium">邮箱</span>
            <span className="text-muted-foreground">{detail.email}</span>
          </div>
          <FormRenderer<UpdateValues>
            schema={userUpdateSchema}
            defaultValues={{ fullName: detail.fullName }}
            onSubmit={async (values, { setFieldErrors }) => {
              if (!id) return;
              setError(null);
              try {
                await updateUser(id, { fullName: values.fullName });
                const toAdd = roleIds.filter(
                  (r) => !initialRoleIdsRef.current.includes(r),
                );
                const toRemove = initialRoleIdsRef.current.filter(
                  (r) => !roleIds.includes(r),
                );
                await Promise.all([
                  ...toAdd.map((rid) => assignRole(id, rid)),
                  ...toRemove.map((rid) => revokeRole(id, rid)),
                ]);
                nav("/admin/users");
              } catch (err) {
                handleProblemDetails(err, setFieldErrors);
              }
            }}
          >
            <RoleAssignmentPanel
              initialRoleIds={initialRoleIdsRef.current}
              onSelectionChange={setRoleIds}
            />
            <div className="flex gap-2">
              <Button type="submit">保存</Button>
              <Button type="button" variant="ghost" onClick={() => nav(-1)}>
                取消
              </Button>
            </div>
          </FormRenderer>
        </>
      ) : null}
    </div>
  );
}
