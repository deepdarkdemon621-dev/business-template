import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { NumberField } from "../fields/NumberField";

function Harness({ name, schema }: { name: string; schema: Record<string, unknown> }) {
  const { register } = useForm();
  return <NumberField name={name} schema={schema} register={register} />;
}

describe("NumberField", () => {
  it("renders an input[type=number] with the field title", () => {
    render(<Harness name="age" schema={{ type: "number", title: "Age" }} />);
    const input = screen.getByLabelText("Age");
    expect(input).toHaveAttribute("type", "number");
  });

  it("applies min/max from schema", () => {
    render(<Harness name="age" schema={{ type: "number", title: "Age", minimum: 0, maximum: 120 }} />);
    const input = screen.getByLabelText("Age");
    expect(input).toHaveAttribute("min", "0");
    expect(input).toHaveAttribute("max", "120");
  });
});
