import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FormRenderer } from "../FormRenderer";

const simpleSchema = {
  type: "object",
  properties: {
    name: { type: "string", title: "Name" },
    age: { type: "number", title: "Age", minimum: 0 },
    active: { type: "boolean", title: "Active" },
  },
  required: ["name"],
};

describe("FormRenderer", () => {
  it("renders each field from the schema", () => {
    render(
      <FormRenderer schema={simpleSchema} onSubmit={() => {}}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Age")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Active" })).toBeInTheDocument();
  });

  it("blocks submit when required field is empty", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={simpleSchema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with typed values when valid", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={simpleSchema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("Name"), "Ada");
    await userEvent.type(screen.getByLabelText("Age"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Ada" }),
      expect.anything(),
    );
  });

  it("runs x-rules (mustMatch)", async () => {
    const schema = {
      type: "object",
      properties: {
        a: { type: "string", title: "A" },
        b: { type: "string", title: "B" },
      },
      mustMatch: { a: "a", b: "b" },
    };
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("A"), "x");
    await userEvent.type(screen.getByLabelText("B"), "y");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
