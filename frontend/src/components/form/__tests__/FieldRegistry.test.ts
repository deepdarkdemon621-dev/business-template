import { describe, expect, it } from "vitest";
import { resolveFieldComponent } from "../FieldRegistry";

describe("FieldRegistry.resolveFieldComponent", () => {
  it("returns StringField for {type: 'string'}", () => {
    const Comp = resolveFieldComponent({ type: "string" });
    expect(Comp.displayName || Comp.name).toBe("StringField");
  });

  it("respects x-widget override", () => {
    const Comp = resolveFieldComponent({ type: "string", "x-widget": "date" });
    expect(Comp.displayName || Comp.name).toBe("DateField");
  });

  it("returns EnumField for schemas with enum array", () => {
    const Comp = resolveFieldComponent({ type: "string", enum: ["a", "b"] });
    expect(Comp.displayName || Comp.name).toBe("EnumField");
  });

  it("throws for unsupported type", () => {
    expect(() => resolveFieldComponent({ type: "whatever" })).toThrow();
  });
});
