import type { Config } from "tailwindcss";
import { tokens } from "./src/lib/design-tokens";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: tokens.colors.background,
        foreground: tokens.colors.foreground,
        muted: {
          DEFAULT: tokens.colors.muted,
          foreground: tokens.colors.mutedForeground,
        },
        border: tokens.colors.border,
        input: tokens.colors.input,
        primary: {
          DEFAULT: tokens.colors.primary,
          foreground: tokens.colors.primaryForeground,
        },
        destructive: {
          DEFAULT: tokens.colors.destructive,
          foreground: tokens.colors.destructiveForeground,
        },
        success: {
          DEFAULT: tokens.colors.success,
          foreground: tokens.colors.successForeground,
        },
        warning: {
          DEFAULT: tokens.colors.warning,
          foreground: tokens.colors.warningForeground,
        },
      },
      borderRadius: tokens.radius,
      fontSize: tokens.fontSize,
    },
  },
  plugins: [],
} satisfies Config;
