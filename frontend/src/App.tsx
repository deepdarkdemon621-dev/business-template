import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { LoginPage } from "@/modules/auth/LoginPage";
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
