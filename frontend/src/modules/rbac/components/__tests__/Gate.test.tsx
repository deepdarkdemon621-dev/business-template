import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Gate } from "../Gate";
import { PermissionsContext } from "@/modules/rbac/PermissionsProvider";

describe("Gate", () => {
  it("renders children when allowed", () => {
    render(
      <PermissionsContext.Provider
        value={{
          isSuperadmin: true,
          permissions: {},
          isLoading: false,
          refetch: async () => {},
        }}
      >
        <Gate permission="user:delete">
          <span>visible</span>
        </Gate>
      </PermissionsContext.Provider>,
    );
    expect(screen.getByText("visible")).toBeInTheDocument();
  });
  it("renders fallback when denied", () => {
    render(
      <PermissionsContext.Provider
        value={{
          isSuperadmin: false,
          permissions: {},
          isLoading: false,
          refetch: async () => {},
        }}
      >
        <Gate permission="user:delete" fallback={<span>nope</span>}>
          <span>visible</span>
        </Gate>
      </PermissionsContext.Provider>,
    );
    expect(screen.getByText("nope")).toBeInTheDocument();
  });
});
