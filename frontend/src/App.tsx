import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/layout/AppShell";
import { PermissionsProvider } from "@/modules/rbac/PermissionsProvider";
import { ForbiddenPage } from "@/modules/rbac/ForbiddenPage";
import { LoginPage } from "@/modules/auth/LoginPage";
import { PasswordResetRequestPage } from "@/modules/auth/PasswordResetRequestPage";
import { PasswordResetConfirmPage } from "@/modules/auth/PasswordResetConfirmPage";
import { PasswordChangePage } from "@/modules/auth/PasswordChangePage";
import { SessionsPage } from "@/modules/auth/SessionsPage";
import { RequireAuth } from "@/modules/auth/components/RequireAuth";
import { DashboardPage } from "@/modules/dashboard/DashboardPage";
import { UserListPage } from "@/modules/user/UserListPage";
import { UserEditPage } from "@/modules/user/UserEditPage";

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
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/password-change" element={<PasswordChangePage />} />
              <Route path="/me/sessions" element={<SessionsPage />} />
              <Route path="/admin/users" element={<UserListPage />} />
              <Route path="/admin/users/new" element={<UserEditPage mode="create" />} />
              <Route path="/admin/users/:id" element={<UserEditPage mode="edit" />} />
            </Route>
          </Routes>
        </PermissionsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
