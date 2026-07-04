import { cn } from "@/lib/utils";

const SIZES = {
  xs: "h-5 w-5 rounded-[5px]",
  sm: "h-6 w-6 rounded-md",
  md: "h-8 w-8 rounded-lg",
  lg: "h-10 w-10 rounded-xl",
  xl: "h-12 w-12 rounded-xl",
} as const;

type Size = keyof typeof SIZES;

interface Props {
  size?: Size;
  className?: string;
  /** Unique gradient id when multiple marks render on one page. */
  gradientId?: string;
}

/** Gradient monogram — matches app/icon.svg and docs/images/trustops-logo.svg */
export function TrustOpsMark({
  size = "md",
  className,
  gradientId = "trustops-mark-gradient",
}: Props) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-label="TrustOps"
      className={cn("flex-none", SIZES[size], className)}
    >
      <title>TrustOps</title>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4f7cff" />
          <stop offset="100%" stopColor="#30c7d2" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      <path d="M8 9h16v4.2h-5.9V26h-4.2V13.2H8z" fill="#fff" />
    </svg>
  );
}
