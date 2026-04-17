import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { DateField } from "../fields/DateField";

function Harness({ name, schema }: { name: string; schema: Record<string, unknown> }) {
  const { register } = useForm();
  return <DateField name={name} schema={schema} register={register} />;
}

describe("DateField", () => {
  it("renders an input[type=date] with the field title", () => {
    render(<Harness name="startsOn" schema={{ type: "string", title: "Starts on", "x-widget": "date" }} />);
    const input = screen.getByLabelText("Starts on");
    expect(input).toHaveAttribute("type", "date");
  });
});
