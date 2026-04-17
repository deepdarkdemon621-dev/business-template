import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { EnumField } from "../fields/EnumField";

function Harness({ name, schema }: { name: string; schema: any }) {
  const { register } = useForm();
  return <EnumField name={name} schema={schema} register={register} />;
}

describe("EnumField", () => {
  it("renders a combobox with the provided enum values", () => {
    render(
      <Harness
        name="status"
        schema={{ type: "string", title: "Status", enum: ["draft", "open", "closed"] }}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Status" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "draft" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "open" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "closed" })).toBeInTheDocument();
  });
});
