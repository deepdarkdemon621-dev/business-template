import { useState } from "react";
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";

const schema = {
  type: "object",
  properties: {
    email: { type: "string", title: "Email", format: "email" },
  },
  required: ["email"],
};

export function PasswordResetRequestPage() {
  const [sent, setSent] = useState(false);

  if (sent) {
    return (
      <div className="mx-auto mt-20 max-w-sm">
        <h1 className="mb-4 text-2xl font-bold">Check Your Email</h1>
        <p className="text-sm text-muted-foreground">
          If that email is registered, a password reset link has been sent.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto mt-20 max-w-sm">
      <h1 className="mb-6 text-2xl font-bold">Reset Password</h1>
      <FormRenderer
        schema={schema}
        onSubmit={async (values) => {
          await client.post("/auth/password-reset/request", values);
          setSent(true);
        }}
      >
        <button
          type="submit"
          className="mt-2 w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Send Reset Link
        </button>
      </FormRenderer>
    </div>
  );
}
