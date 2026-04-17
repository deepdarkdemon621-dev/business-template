import "@testing-library/jest-dom/vitest";

// jsdom does not implement ResizeObserver; Radix UI primitives (Checkbox
// via useSize) require it.  Provide a no-op stub so tests can render
// components that transitively depend on it.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof globalThis.ResizeObserver;
}
