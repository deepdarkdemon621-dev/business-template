import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "@/lib/auth/AuthProvider";
import { LoginPage } from "../LoginPage";

function renderLogin(overrides: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = {
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    ...overrides,
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <LoginPage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  });
});
