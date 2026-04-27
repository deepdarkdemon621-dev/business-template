import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DiffView } from "../components/DiffView";

describe("DiffView", () => {
  it("renders create variant with green border and after JSON", () => {
    const { container } = render(
      <DiffView action="create" before={null} after={{ email: "a@x" }} changes={null} />,
    );
    expect(container.querySelector(".border-l-green-500")).toBeInTheDocument();
    expect(screen.getByText(/a@x/)).toBeInTheDocument();
  });

  it("renders delete variant with red border and before JSON", () => {
    const { container } = render(
      <DiffView action="delete" before={{ code: "r1" }} after={null} changes={null} />,
    );
    expect(container.querySelector(".border-l-red-500")).toBeInTheDocument();
    expect(screen.getByText(/r1/)).toBeInTheDocument();
  });

  it("renders update variant as a 2-column table with arrows", () => {
    render(
      <DiffView
        action="update"
        before={null}
        after={null}
        changes={{ name: ["Old", "New"], is_active: [true, false] }}
      />,
    );
    expect(screen.getByText("name")).toBeInTheDocument();
    expect(screen.getByText("Old")).toBeInTheDocument();
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.getAllByText("→")).toHaveLength(2);
  });

  it("renders nothing when all inputs are null (auth event)", () => {
    const { container } = render(
      <DiffView action="login" before={null} after={null} changes={null} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
