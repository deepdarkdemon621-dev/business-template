import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DateRangePicker } from "../date-range-picker";

describe("DateRangePicker", () => {
  it("renders placeholder when no value is set", () => {
    render(
      <DateRangePicker value={{}} onChange={vi.fn()} placeholder="Pick dates" />,
    );
    expect(screen.getByText("Pick dates")).toBeInTheDocument();
  });

  it("renders formatted dates when both from and to are set", () => {
    render(
      <DateRangePicker
        value={{ from: new Date(2024, 0, 10), to: new Date(2024, 0, 20) }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText("2024-01-10 → 2024-01-20")).toBeInTheDocument();
  });

  it("renders partial label when only from is set", () => {
    render(
      <DateRangePicker
        value={{ from: new Date(2024, 2, 5) }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText("2024-03-05 →")).toBeInTheDocument();
  });
});
