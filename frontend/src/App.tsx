import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { LoginPage } from "@/modules/auth/LoginPage";
import { PasswordResetRequestPage } from "@/modules/auth/PasswordResetRequestPage";
import { PasswordResetConfirmPage } from "@/modules/auth/PasswordResetConfirmPage";
import { PasswordChangePage } from "@/modules/auth/PasswordChangePage";
import { SessionsPage } from "@/modules/auth/SessionsPage";
import { RequireAuth } from "@/modules/auth/components/RequireAuth";

function DashboardPlaceholder() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <h1 className="text-2xl font-bold">Dashboard (coming soon)</h1>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/password-reset" element={<PasswordResetRequestPage />} />
          <Route path="/password-reset/confirm" element={<PasswordResetConfirmPage />} />
          <Route
            path="/password-change"
            element={
              <RequireAuth>
                <PasswordChangePage />
              </RequireAuth>
            }
          />
          <Route
            path="/me/sessions"
            element={
              <RequireAuth>
                <SessionsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/"
            element={
              <RequireAuth>
                <DashboardPlaceholder />
              </RequireAuth>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
