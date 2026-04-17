import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    currentPassword: { type: "string", title: "Current Password" },
    newPassword: { type: "string", title: "New Password" },
    confirm: { type: "string", title: "Confirm New Password" },
  },
  required: ["currentPassword", "newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
  passwordPolicy: { field: "newPassword" },
};

export function PasswordChangePage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="mx-auto mt-20 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold">Change Password</h1>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <FormRenderer
        schema={schema}
        onSubmit={async (values, { setFieldErrors }) => {
          setError(null);
          try {
            await client.put("/me/password", {
              currentPassword: values.currentPassword,
              newPassword: values.newPassword,
              confirm: values.confirm,
            });
            navigate("/");
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
          Change Password
        </button>
      </FormRenderer>
    </div>
  );
}
