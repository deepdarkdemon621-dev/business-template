import { describe, expect, it } from "vitest";
import { isProblemDetails, type ProblemDetails } from "../problem-details";

describe("isProblemDetails", () => {
  it("returns true for a minimal valid body", () => {
    const body: ProblemDetails = {
      type: "about:blank",
      title: "Not Found",
      status: 404,
      detail: "x",
      code: "user.not-found",
    };
    expect(isProblemDetails(body)).toBe(true);
  });

  it("accepts optional errors and guardViolation", () => {
    const body = {
      type: "about:blank",
      status: 409,
      detail: "x",
      code: "u.x",
      errors: [{ field: "email", code: "format" }],
      guardViolation: { guard: "NoDependents", params: { relation: "users" } },
    };
    expect(isProblemDetails(body)).toBe(true);
  });

  it("returns false for unrelated shapes", () => {
    expect(isProblemDetails({ message: "oops" })).toBe(false);
    expect(isProblemDetails(null)).toBe(false);
    expect(isProblemDetails("oops")).toBe(false);
    expect(isProblemDetails({ status: 500, detail: "x" })).toBe(false);
  });
});
