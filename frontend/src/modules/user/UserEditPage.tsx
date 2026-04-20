import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { problemMessage } from "@/lib/problem-details";
import { createUser, updateUser } from "./api";

export type UserEditPageProps = { mode: "create" | "edit" };

export function UserEditPage({ mode }: UserEditPageProps) {
  const nav = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Edit-mode loader added in Task F3.

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "create") {
        const created = await createUser({
          email,
          password,
          fullName,
          mustChangePassword: true,
        });
        nav(`/admin/users/${created.id}`);
      } else if (mode === "edit" && id) {
        await updateUser(id, { fullName });
        nav("/admin/users");
      }
    } catch (err) {
      setError(problemMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-lg flex-col gap-4">
      <h1 className="text-xl font-semibold">
        {mode === "create" ? "新建用户" : "编辑用户"}
      </h1>
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">邮箱 *</Label>
        <Input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={mode === "edit"}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="fullName">姓名 *</Label>
        <Input
          id="fullName"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </div>
      {mode === "create" ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">密码</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            至少 10 个字符，需包含字母和数字。
          </p>
        </div>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {mode === "create" ? "创建" : "保存"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => nav(-1)}>
          取消
        </Button>
      </div>
    </form>
  );
}
