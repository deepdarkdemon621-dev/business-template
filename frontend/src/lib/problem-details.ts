export interface FieldError {
  field: string;
  code: string;
  message?: string;
}

export interface GuardViolationCtx {
  guard: string;
  params: Record<string, unknown>;
}

export interface ProblemDetails {
  type: string;
  title?: string;
  status: number;
  detail: string;
  code: string;
  errors?: FieldError[];
  guardViolation?: GuardViolationCtx;
}

export function isProblemDetails(x: unknown): x is ProblemDetails {
  if (x === null || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.type === "string" &&
    typeof o.status === "number" &&
    typeof o.detail === "string" &&
    typeof o.code === "string"
  );
}

export function problemMessage(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const resp = (err as { response?: { data?: unknown } }).response;
    if (resp && resp.data && isProblemDetails(resp.data)) {
      return resp.data.detail;
    }
  }
  if (err instanceof Error) return err.message;
  return "请求失败，请重试。";
}
