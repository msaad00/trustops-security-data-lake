import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex max-w-full min-w-0 items-center rounded-full px-2 py-0.5 text-xs font-extrabold",
  {
    variants: {
      tone: {
        default: "bg-slate-100 text-slate-600",
        ready: "bg-emerald-100 text-emerald-700",
        attention: "bg-amber-100 text-amber-800",
        critical: "bg-rose-100 text-rose-700",
        info: "bg-blue-100 text-blue-700",
      },
    },
    defaultVariants: { tone: "default" },
  },
);

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone, className }))} {...props} />;
}
