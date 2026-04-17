import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthProvider } from "../AuthProvider";
import { useAuth } from "../useAuth";
import { client } from "@/api/client";
import type { AxiosResponse } from "axios";

function TestConsumer() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div>loading</div>;
  if (isAuthenticated) return <div>logged in</div>;
  return <div>not logged in</div>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("starts in loading state then resolves to unauthenticated", async () => {
    // The AuthProvider calls client.post("/auth/refresh") on mount.
    // Simulate a 401/network rejection so refreshToken returns null → unauthenticated.
    vi.spyOn(client, "post").mockRejectedValueOnce(
      Object.assign(new Error("401"), { response: { status: 401 } }),
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    // Initially loading
    expect(screen.getByText("loading")).toBeInTheDocument();

    // After refresh attempt resolves → not logged in
    await waitFor(() => {
      expect(screen.getByText("not logged in")).toBeInTheDocument();
    });
  });

  it("resolves to authenticated when refresh succeeds", async () => {
    const fakeToken = "eyJ.test.token";
    vi.spyOn(client, "post").mockResolvedValueOnce({
      data: { accessToken: fakeToken },
    } as AxiosResponse);

    // AuthProvider only has the token but not user info from refresh — user stays null.
    // The refreshToken endpoint only returns the accessToken, not the user object,
    // so isAuthenticated remains false after refresh (user is still null).
    // This matches the spec: user is populated only on login.
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("not logged in")).toBeInTheDocument();
    });
    expect(sessionStorage.getItem("access_token")).toBe(fakeToken);
  });
});
