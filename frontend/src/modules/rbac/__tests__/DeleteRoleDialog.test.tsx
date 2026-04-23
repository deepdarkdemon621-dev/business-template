import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DeleteRoleDialog } from "../components/DeleteRoleDialog";

describe("DeleteRoleDialog", () => {
  it("shows cascade count in body copy", () => {
    render(
      <DeleteRoleDialog
        open
        roleCode="tester"
        roleName="Tester"
        userCount={5}
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.getByText(/assigned to 5 users/i)).toBeInTheDocument();
  });

  it("disables confirm until exact role code typed", () => {
    const onConfirm = vi.fn();
    render(
      <DeleteRoleDialog
        open
        roleCode="tester"
        roleName="Tester"
        userCount={0}
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );
    const confirm = screen.getByRole("button", { name: /confirm delete/i });
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/type the role code/i), {
      target: { value: "test" },
    });
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/type the role code/i), {
      target: { value: "tester" },
    });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("does not render when open=false", () => {
    render(
      <DeleteRoleDialog
        open={false}
        roleCode="tester"
        roleName="Tester"
        userCount={0}
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
