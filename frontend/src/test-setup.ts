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

// jsdom lacks pointer-capture APIs used by Radix Select.
if (typeof Element.prototype.hasPointerCapture === "undefined") {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
}

// jsdom lacks scrollIntoView used by Radix Select items.
if (typeof Element.prototype.scrollIntoView === "undefined") {
  Element.prototype.scrollIntoView = () => {};
}
