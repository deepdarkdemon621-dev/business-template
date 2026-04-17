import { describe, expect, it, beforeEach } from "vitest";
import { getToken, setToken, clearToken } from "../storage";

describe("auth storage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns null when no token stored", () => {
    expect(getToken()).toBeNull();
  });

  it("stores and retrieves a token", () => {
    setToken("my-jwt");
    expect(getToken()).toBe("my-jwt");
  });

  it("clears the token", () => {
    setToken("my-jwt");
    clearToken();
    expect(getToken()).toBeNull();
  });
});
