import { useState } from "react";
import { FormRenderer } from "@/components/form/FormRenderer";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/lib/problem-details";
import { createDepartment, updateDepartment } from "../api";
import { departmentCreateSchema, departmentUpdateSchema } from "../schema";
import type { DepartmentNode } from "../types";

export type EditModalState =
  | { mode: "create"; parentId: string }
  | { mode: "rename"; node: DepartmentNode };

export function DepartmentEditModal(props: {
  state: EditModalState;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const { state, onClose, onSaved } = props;
  const [error, setError] = useState<string | null>(null);
  const isCreate = state.mode === "create";
  const schema = isCreate ? departmentCreateSchema : departmentUpdateSchema;
  const defaults = isCreate ? { name: "" } : { name: state.node.name };
  const title = isCreate ? "新建子部门" : "重命名";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="flex w-full max-w-md flex-col gap-4 rounded bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">{title}</h2>
        <FormRenderer<{ name: string }>
          schema={schema}
          defaultValues={defaults}
          onSubmit={async (values, { setFieldErrors }) => {
            setError(null);
            try {
              if (state.mode === "create") {
                await createDepartment({
                  name: values.name,
                  parentId: state.parentId,
                });
              } else {
                await updateDepartment(state.node.id, { name: values.name });
              }
              await onSaved();
            } catch (err) {
              const msg = problemMessage(err);
              const errObj = err as { errors?: Array<{ field?: string; message?: string }> };
              if (errObj?.errors?.length) {
                setFieldErrors(
                  Object.fromEntries(
                    errObj.errors.map((e) => [e.field ?? "name", e.message ?? msg]),
                  ),
                );
              } else {
                setError(msg);
              }
            }
          }}
        >
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              取消
            </Button>
            <Button type="submit">保存</Button>
          </div>
        </FormRenderer>
      </div>
    </div>
  );
}
