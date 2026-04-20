import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <header className="flex h-14 items-center justify-between border-b px-6">
      <div className="font-semibold">Business Template</div>
      <div className="flex items-center gap-3 text-sm">
        {user ? <span>{user.fullName}</span> : null}
        <Button variant="outline" size="sm" onClick={() => nav("/password-change")}>
          改密
        </Button>
        <Button variant="outline" size="sm" onClick={() => nav("/me/sessions")}>
          会话
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={async () => {
            try {
              await logout();
            } finally {
              nav("/login");
            }
          }}
        >
          登出
        </Button>
      </div>
    </header>
  );
}
