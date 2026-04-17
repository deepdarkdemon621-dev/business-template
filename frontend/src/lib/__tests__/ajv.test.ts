import { describe, expect, it } from "vitest";
import { ajv } from "../ajv";

describe("ajv singleton", () => {
  it("exposes a single instance across imports", async () => {
    const again = (await import("../ajv")).ajv;
    expect(ajv).toBe(again);
  });

  it("mustMatch passes when fields match", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { a: { type: "string" }, b: { type: "string" } },
      mustMatch: { a: "a", b: "b" },
    });
    expect(validate({ a: "x", b: "x" })).toBe(true);
    expect(validate({ a: "x", b: "y" })).toBe(false);
  });

  it("dateOrder passes when end > start", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { startsOn: { type: "string" }, endsOn: { type: "string" } },
      dateOrder: { start: "startsOn", end: "endsOn" },
    });
    expect(validate({ startsOn: "2026-04-01", endsOn: "2026-04-17" })).toBe(true);
    expect(validate({ startsOn: "2026-04-17", endsOn: "2026-04-01" })).toBe(false);
  });

  it("dateOrder skips when either side missing", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { startsOn: { type: "string" }, endsOn: { type: "string" } },
      dateOrder: { start: "startsOn", end: "endsOn" },
    });
    expect(validate({})).toBe(true);
    expect(validate({ startsOn: "2026-04-01" })).toBe(true);
  });
});

describe("passwordPolicy keyword", () => {
  it("passes valid password", () => {
    const schema = {
      type: "object",
      properties: { newPassword: { type: "string" } },
      passwordPolicy: { field: "newPassword" },
    };
    const validate = ajv.compile(schema);
    expect(validate({ newPassword: "MySecret123" })).toBe(true);
  });

  it("rejects password too short", () => {
    const schema = {
      type: "object",
      properties: { newPassword: { type: "string" } },
      passwordPolicy: { field: "newPassword" },
    };
    const validate = ajv.compile(schema);
    expect(validate({ newPassword: "Ab1" })).toBe(false);
  });

  it("rejects password without digit", () => {
    const schema = {
      type: "object",
      properties: { newPassword: { type: "string" } },
      passwordPolicy: { field: "newPassword" },
    };
    const validate = ajv.compile(schema);
    expect(validate({ newPassword: "abcdefghijk" })).toBe(false);
  });
});
