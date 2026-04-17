import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    newPassword: { type: "string", title: "New Password" },
    confirm: { type: "string", title: "Confirm Password" },
  },
  required: ["newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
  passwordPolicy: { field: "newPassword" },
};

export function PasswordResetConfirmPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const token = searchParams.get("token");

  if (!token) {
    return (
      <div className="mx-auto mt-20 max-w-sm">
        <p className="text-sm text-red-600">Invalid or missing reset token.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-20 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold">Set New Password</h1>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <FormRenderer
        schema={schema}
        onSubmit={async (values, { setFieldErrors }) => {
          setError(null);
          try {
            await client.post("/auth/password-reset/confirm", {
              token,
              newPassword: values.newPassword,
              confirm: values.confirm,
            });
            navigate("/login");
          } catch (err) {
            if (isProblemDetails(err)) {
              if (err.errors?.length) {
                setFieldErrors(
                  Object.fromEntries(err.errors.map((e) => [e.field, e.message ?? e.code])),
                );
              } else {
                setError(err.detail);
              }
            } else {
              setError("An unexpected error occurred.");
            }
          }
        }}
      >
        <button
          type="submit"
          className="mt-2 w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Reset Password
        </button>
      </FormRenderer>
    </div>
  );
}
