import { describe, expect, it, vi, afterEach } from "vitest";
import { client } from "../client";
import { isProblemDetails } from "@/lib/problem-details";

// Reset adapter after each test so tests don't bleed into each other
afterEach(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delete (client.defaults as any).adapter;
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("rejects with a ProblemDetails payload when server returns problem data", async () => {
    const pd = {
      type: "about:blank",
      title: "Conflict",
      status: 409,
      detail: "nope",
      code: "dep.has-users",
    };

    // Mock adapter to simulate a Problem Details error response.
    // The adapter returns a rejected promise; Axios passes the rejection
    // through the response interceptor chain.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (client.defaults as any).adapter = async (config: unknown) => {
      const err = Object.assign(new Error("Request failed with status code 409"), {
        isAxiosError: true,
        response: { status: 409, data: pd, headers: {}, config, statusText: "Conflict" },
        config,
      });
      return Promise.reject(err);
    };

    try {
      await client.get("/x");
      expect.fail("should have rejected");
    } catch (err) {
      expect(isProblemDetails(err)).toBe(true);
    }
  });

  it("rejects with the raw error for non-Problem responses", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (client.defaults as any).adapter = async (config: unknown) => {
      const err = Object.assign(new Error("Request failed with status code 500"), {
        isAxiosError: true,
        response: { status: 500, data: "boom", headers: {}, config, statusText: "Error" },
        config,
      });
      return Promise.reject(err);
    };

    try {
      await client.get("/x");
      expect.fail("should have rejected");
    } catch (err: unknown) {
      expect(isProblemDetails(err)).toBe(false);
      // err is the raw AxiosError (not unwrapped) — check it has response
      expect((err as { response?: { status: number } }).response?.status).toBe(500);
    }
  });
});
