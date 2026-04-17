import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FormRenderer } from "@/components/form/FormRenderer";
import { useAuth } from "@/lib/auth";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    email: { type: "string", title: "Email", format: "email" },
    password: { type: "string", title: "Password" },
  },
  required: ["email", "password"],
};

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="mx-auto mt-20 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold">Log In</h1>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <FormRenderer
        schema={schema}
        onSubmit={async (values, { setFieldErrors }) => {
          setError(null);
          try {
            const { mustChangePassword } = await login(
              values.email as string,
              values.password as string,
            );
            if (mustChangePassword) {
              navigate("/password-change");
            } else {
              navigate("/");
            }
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
          Log In
        </button>
      </FormRenderer>
    </div>
  );
}
