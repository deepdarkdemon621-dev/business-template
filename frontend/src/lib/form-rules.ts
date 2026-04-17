import type Ajv from "ajv";

interface MustMatchParams {
  a: string;
  b: string;
}

interface DateOrderParams {
  start: string;
  end: string;
}

export function registerRuleKeywords(ajv: Ajv): void {
  ajv.addKeyword({
    keyword: "mustMatch",
    type: "object",
    errors: true,
    validate: function mustMatch(params: MustMatchParams, data: Record<string, unknown>) {
      const ok = data[params.a] === data[params.b];
      if (!ok) {
        // @ts-expect-error — Ajv attaches errors on the function
        mustMatch.errors = [
          { keyword: "mustMatch", message: `${params.a} must equal ${params.b}`, params },
        ];
      }
      return ok;
    },
  });

  ajv.addKeyword({
    keyword: "dateOrder",
    type: "object",
    errors: true,
    validate: function dateOrder(params: DateOrderParams, data: Record<string, unknown>) {
      const s = data[params.start];
      const e = data[params.end];
      if (s == null || e == null) return true;
      if (typeof s !== "string" || typeof e !== "string") return false;
      const ok = new Date(e) > new Date(s);
      if (!ok) {
        // @ts-expect-error — Ajv attaches errors on the function
        dateOrder.errors = [
          { keyword: "dateOrder", message: `${params.end} must be after ${params.start}`, params },
        ];
      }
      return ok;
    },
  });
}
