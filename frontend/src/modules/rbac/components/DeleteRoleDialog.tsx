import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface DeleteRoleDialogProps {
  open: boolean;
  roleCode: string;
  roleName: string;
  userCount: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteRoleDialog({
  open,
  roleCode,
  roleName,
  userCount,
  onConfirm,
  onCancel,
}: DeleteRoleDialogProps) {
  const [typed, setTyped] = useState("");
  if (!open) return null;

  const canConfirm = typed === roleCode;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80"
    >
      <div className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg">
        <h2 className="text-lg font-semibold">Delete role &quot;{roleName}&quot;?</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This role is assigned to {userCount} users. Deleting will revoke the role
          from all of them. This cannot be undone.
        </p>
        <div className="mt-4 space-y-2">
          <Label htmlFor="confirm-role-code">
            Type the role code <span className="font-mono">{roleCode}</span> to confirm
          </Label>
          <Input
            id="confirm-role-code"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!canConfirm}
            onClick={onConfirm}
          >
            Confirm delete
          </Button>
        </div>
      </div>
    </div>
  );
}
