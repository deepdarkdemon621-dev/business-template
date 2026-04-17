import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "@/lib/auth/AuthProvider";
import { RequireAuth } from "../components/RequireAuth";

function renderWithAuth(value: Partial<AuthContextValue>) {
  const full: AuthContextValue = {
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    ...value,
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={full}>
        <RequireAuth>
          <div>protected content</div>
        </RequireAuth>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  it("shows children when authenticated", () => {
    renderWithAuth({
      isAuthenticated: true,
      user: {
        id: "1",
        email: "a@b.com",
        fullName: "A",
        departmentId: null,
        isActive: true,
        mustChangePassword: false,
      },
    });
    expect(screen.getByText("protected content")).toBeInTheDocument();
  });

  it("redirects when not authenticated", () => {
    renderWithAuth({ isAuthenticated: false });
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });

  it("shows loading when isLoading", () => {
    renderWithAuth({ isLoading: true });
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});
