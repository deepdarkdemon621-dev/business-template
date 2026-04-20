import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PermissionsContext } from "../PermissionsProvider";
import { usePermissions } from "../usePermissions";

function Probe({
  code,
  minScope,
}: {
  code: string;
  minScope?: "global" | "dept_tree" | "dept" | "own";
}) {
  const { has } = usePermissions();
  return <span>{has(code, minScope) ? "yes" : "no"}</span>;
}

describe("usePermissions", () => {
  it("superadmin bypasses", () => {
    render(
      <PermissionsContext.Provider
        value={{
          isSuperadmin: true,
          permissions: {},
          isLoading: false,
          refetch: async () => {},
        }}
      >
        <Probe code="user:read" />
      </PermissionsContext.Provider>,
    );
    expect(screen.getByText("yes")).toBeInTheDocument();
  });
  it("returns false when code missing", () => {
    render(
      <PermissionsContext.Provider
        value={{
          isSuperadmin: false,
          permissions: {},
          isLoading: false,
          refetch: async () => {},
        }}
      >
        <Probe code="user:read" />
      </PermissionsContext.Provider>,
    );
    expect(screen.getByText("no")).toBeInTheDocument();
  });
  it("returns true when scope >= minScope", () => {
    render(
      <PermissionsContext.Provider
        value={{
          isSuperadmin: false,
          permissions: { "user:read": "global" },
          isLoading: false,
          refetch: async () => {},
        }}
      >
        <Probe code="user:read" minScope="dept_tree" />
      </PermissionsContext.Provider>,
    );
    expect(screen.getByText("yes")).toBeInTheDocument();
  });
});
