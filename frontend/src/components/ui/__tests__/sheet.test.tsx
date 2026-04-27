import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "../sheet";

describe("Sheet", () => {
  it("renders trigger without crashing", () => {
    render(
      <Sheet>
        <SheetTrigger>Open Sheet</SheetTrigger>
        <SheetContent>
          <SheetTitle>Test Sheet</SheetTitle>
          <p>Content</p>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("Open Sheet")).toBeInTheDocument();
  });

  it("renders left-side variant trigger", () => {
    render(
      <Sheet>
        <SheetTrigger>Open Left</SheetTrigger>
        <SheetContent side="left">
          <SheetTitle>Left Sheet</SheetTitle>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("Open Left")).toBeInTheDocument();
  });
});
