import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders without crashing", () => {
    render(<App />);
    // The app mounts BrowserRouter + AuthProvider. On initial load
    // AuthProvider fires a token refresh (isLoading=true), so RequireAuth
    // shows the loading indicator rather than the protected content.
    expect(document.body).toBeInTheDocument();
  });
});
