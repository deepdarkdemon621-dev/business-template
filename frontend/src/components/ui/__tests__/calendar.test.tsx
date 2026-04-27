import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Calendar } from "../calendar";

describe("Calendar", () => {
  it("renders without crashing", () => {
    render(<Calendar />);
    // DayPicker renders navigation buttons; presence of a button confirms mount
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });

  it("renders in range mode without crashing", () => {
    render(
      <Calendar
        mode="range"
        selected={{ from: new Date(2024, 0, 10), to: new Date(2024, 0, 20) }}
      />,
    );
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });
});
