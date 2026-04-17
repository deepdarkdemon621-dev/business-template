import { describe, expect, it } from "vitest";
import type { Page, PageQuery } from "../pagination";

describe("pagination types", () => {
  it("Page<T> accepts items and metadata", () => {
    const p: Page<{ id: number }> = {
      items: [{ id: 1 }],
      total: 1,
      page: 1,
      size: 20,
      hasNext: false,
    };
    expect(p.items.length).toBe(1);
  });

  it("PageQuery fields are all optional", () => {
    const q: PageQuery = {};
    expect(q).toEqual({});
  });
});
