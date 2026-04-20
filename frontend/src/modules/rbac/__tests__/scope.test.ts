import { describe, it, expect } from "vitest";
import { widest, atLeast } from "../scope";

describe("scope", () => {
  it("widest returns the wider of two", () => {
    expect(widest("own", "dept_tree")).toBe("dept_tree");
    expect(widest("global", "dept")).toBe("global");
  });
  it("atLeast compares priority", () => {
    expect(atLeast("global", "dept_tree")).toBe(true);
    expect(atLeast("own", "global")).toBe(false);
  });
});
