import { cn } from "@/lib/utils";
import { BRAND } from "@/lib/brand";

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
  gradientId?: string;
}

/** Trust Data Lake geometric monogram. */
export function TrustOpsMark({
  size = "md",
  className,
  gradientId = "trustops-mark-gradient",
}: Props) {
  return (
    <svg
      viewBox="0 0 32 32"
      role="img"
      aria-label={BRAND.name}
      className={cn("flex-none", SIZES[size], className)}
    >
      <title>{BRAND.name}</title>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4f7cff" />
          <stop offset="100%" stopColor="#30c7d2" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="#071426" />
      <path
        d="M4 7.5h7M7.5 7.5v16M13.5 7.5v16h3.2c4.5 0 6.8-2.8 6.8-8s-2.3-8-6.8-8h-3.2ZM26 7.5v16h3.5"
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.35"
        strokeLinecap="square"
        strokeLinejoin="round"
      />
      <path
        d="M4 27c5-1.7 8.5 1.7 13.5 0s8.5 1.7 12.5 0"
        stroke="#5eead4"
        strokeWidth="1.25"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}
