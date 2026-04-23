import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RolePermissionMatrix } from "../components/RolePermissionMatrix";
import type { Permission, RolePermissionItem } from "../types";

const samplePerms: Permission[] = [
  { id: "p1", code: "user:read", resource: "user", action: "read", description: "Read a user" },
  { id: "p2", code: "user:create", resource: "user", action: "create", description: "Create a user" },
  { id: "p3", code: "role:read", resource: "role", action: "read", description: "Read a role" },
];

describe("RolePermissionMatrix", () => {
  it("renders rows grouped by resource", () => {
    render(
      <RolePermissionMatrix
        value={[]}
        onChange={() => {}}
        allPermissions={samplePerms}
      />,
    );
    expect(screen.getByText("user:read")).toBeInTheDocument();
    expect(screen.getByText("user:create")).toBeInTheDocument();
    expect(screen.getByText("role:read")).toBeInTheDocument();
  });

  it("shows the current scope as selected", () => {
    const value: RolePermissionItem[] = [
      { permissionCode: "user:read", scope: "global" },
    ];
    render(
      <RolePermissionMatrix
        value={value}
        onChange={() => {}}
        allPermissions={samplePerms}
      />,
    );
    const radio = screen.getByRole("radio", {
      name: /user:read.*global/i,
    }) as HTMLInputElement;
    expect(radio.checked).toBe(true);
  });

  it("emits onChange on scope selection — adds when previously ungranted", () => {
    const onChange = vi.fn();
    render(
      <RolePermissionMatrix
        value={[]}
        onChange={onChange}
        allPermissions={samplePerms}
      />,
    );
    const radio = screen.getByRole("radio", {
      name: /user:read.*global/i,
    });
    fireEvent.click(radio);
    expect(onChange).toHaveBeenCalledWith([
      { permissionCode: "user:read", scope: "global" },
    ]);
  });

  it("emits onChange with scope removed when selecting 'Not granted'", () => {
    const value: RolePermissionItem[] = [
      { permissionCode: "user:read", scope: "global" },
    ];
    const onChange = vi.fn();
    render(
      <RolePermissionMatrix
        value={value}
        onChange={onChange}
        allPermissions={samplePerms}
      />,
    );
    const none = screen.getByRole("radio", { name: /user:read.*not granted/i });
    fireEvent.click(none);
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("disables all radios when disabled=true", () => {
    render(
      <RolePermissionMatrix
        value={[]}
        onChange={() => {}}
        allPermissions={samplePerms}
        disabled
      />,
    );
    const radios = screen.getAllByRole("radio");
    radios.forEach((r) => expect(r).toBeDisabled());
  });
});
