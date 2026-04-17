import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    newPassword: { type: "string", title: "New password" },
    confirm: { type: "string", title: "Confirm" },
  },
  required: ["newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
};

const server = setupServer(
  http.post("/api/v1/password-reset", async () =>
    HttpResponse.json(
      {
        type: "about:blank",
        title: "Unprocessable Entity",
        status: 422,
        detail: "validation failed",
        code: "auth.weak-password",
        errors: [{ field: "newPassword", code: "weak", message: "too short" }],
      },
      { status: 422, headers: { "content-type": "application/problem+json" } },
    ),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("primitives integration", () => {
  it("ajv blocks submit when passwords don't match", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("New password"), "abcdef");
    await userEvent.type(screen.getByLabelText("Confirm"), "zzzzzz");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("surfaces server-side field errors via setFieldErrors", async () => {
    const onSubmit = async (
      values: Record<string, string>,
      { setFieldErrors }: { setFieldErrors: (e: Record<string, string>) => void },
    ) => {
      try {
        await client.post("/password-reset", values);
      } catch (err) {
        if (isProblemDetails(err) && err.errors) {
          setFieldErrors(
            Object.fromEntries(
              err.errors.map((e) => [e.field, e.message ?? e.code]),
            ),
          );
        }
      }
    };

    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("New password"), "match1");
    await userEvent.type(screen.getByLabelText("Confirm"), "match1");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("too short")).toBeInTheDocument();
  });
});
