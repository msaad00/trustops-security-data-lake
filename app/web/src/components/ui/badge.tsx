import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex max-w-full min-w-0 items-center rounded-full px-2 py-0.5 text-xs font-extrabold",
  {
    variants: {
      tone: {
        default:
          "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-200",
        ready:
          "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
        attention:
          "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
        critical:
          "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
        info: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
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
