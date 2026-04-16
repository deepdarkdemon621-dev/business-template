/**
 * Design tokens — single source of truth.
 *
 * Both tailwind.config.ts and runtime components (MUI-less shadcn/ui setup)
 * MUST read from this file. Never hard-code colors / spacing / radii elsewhere.
 *
 * See docs/conventions/03-ui-primitives.md.
 */

export const tokens = {
  colors: {
    background: "hsl(0 0% 100%)",
    foreground: "hsl(240 10% 3.9%)",
    muted: "hsl(240 4.8% 95.9%)",
    mutedForeground: "hsl(240 3.8% 46.1%)",
    border: "hsl(240 5.9% 90%)",
    input: "hsl(240 5.9% 90%)",
    primary: "hsl(221.2 83% 53.3%)",
    primaryForeground: "hsl(210 40% 98%)",
    destructive: "hsl(0 72.2% 50.6%)",
    destructiveForeground: "hsl(0 0% 98%)",
    success: "hsl(142.1 76.2% 36.3%)",
    successForeground: "hsl(0 0% 98%)",
    warning: "hsl(38 92% 50%)",
    warningForeground: "hsl(0 0% 98%)",
  },
  radius: {
    sm: "0.25rem",
    md: "0.5rem",
    lg: "0.75rem",
  },
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
  },
} as const;

export type DesignTokens = typeof tokens;
