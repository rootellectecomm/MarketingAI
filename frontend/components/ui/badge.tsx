import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "success" | "warning" | "danger";
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  const tones = {
    neutral: "bg-[var(--muted)] text-[var(--foreground)]",
    success: "bg-[color-mix(in_srgb,var(--success)_18%,transparent)] text-[var(--success)]",
    warning: "bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[var(--warning)]",
    danger: "bg-[color-mix(in_srgb,var(--danger)_18%,transparent)] text-[var(--danger)]"
  };
  return (
    <span
      className={cn("inline-flex items-center rounded-md px-2 py-1 text-xs font-medium", tones[tone], className)}
      {...props}
    />
  );
}

