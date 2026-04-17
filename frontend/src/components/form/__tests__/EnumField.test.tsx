import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { EnumField } from "../fields/EnumField";

function Harness({ name, schema }: { name: string; schema: Record<string, unknown> }) {
  const { register } = useForm();
  return <EnumField name={name} schema={schema} register={register} />;
}

describe("EnumField", () => {
  it("renders a select trigger with the label", () => {
    render(
      <Harness
        name="status"
        schema={{ type: "string", title: "Status", enum: ["draft", "open", "closed"] }}
      />,
    );
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows options when opened", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        name="status"
        schema={{ type: "string", title: "Status", enum: ["draft", "open", "closed"] }}
      />,
    );
    await user.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: "draft" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "open" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "closed" })).toBeInTheDocument();
  });
});
