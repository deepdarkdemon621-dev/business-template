import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { PermissionsProvider } from "@/modules/rbac/PermissionsProvider";
import { ForbiddenPage } from "@/modules/rbac/ForbiddenPage";
import { LoginPage } from "@/modules/auth/LoginPage";
import { PasswordResetRequestPage } from "@/modules/auth/PasswordResetRequestPage";
import { PasswordResetConfirmPage } from "@/modules/auth/PasswordResetConfirmPage";
import { PasswordChangePage } from "@/modules/auth/PasswordChangePage";
import { SessionsPage } from "@/modules/auth/SessionsPage";
import { RequireAuth } from "@/modules/auth/components/RequireAuth";
import { DashboardPage } from "@/modules/dashboard/DashboardPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PermissionsProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/password-reset" element={<PasswordResetRequestPage />} />
            <Route
              path="/password-reset/confirm"
              element={<PasswordResetConfirmPage />}
            />
            <Route path="/403" element={<ForbiddenPage />} />
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
                  <DashboardPage />
                </RequireAuth>
              }
            />
          </Routes>
        </PermissionsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
