import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { BooleanField } from "../fields/BooleanField";

function Harness({ name, schema }: { name: string; schema: Record<string, unknown> }) {
  const { register } = useForm();
  return <BooleanField name={name} schema={schema} register={register} />;
}

describe("BooleanField", () => {
  it("renders a checkbox with the field title", () => {
    render(<Harness name="agreed" schema={{ type: "boolean", title: "Agree" }} />);
    expect(screen.getByRole("checkbox", { name: "Agree" })).toBeInTheDocument();
  });
});
