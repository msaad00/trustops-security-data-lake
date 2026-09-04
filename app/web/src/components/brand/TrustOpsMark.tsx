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

/** Cloud, agent, and identity sources over lake contours. */
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
      <g
        data-mark="source-types"
        fill="none"
        strokeWidth="1.15"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path
          d="M4.5 7.7h4.7a1.5 1.5 0 0 0 .1-3 2.2 2.2 0 0 0-4.1.6 1.25 1.25 0 0 0-.7 2.4"
          stroke="#4f7cff"
        />
        <path
          d="M16 3.7c.2 1.6.9 2.4 2.5 2.6-1.6.2-2.3 1-2.5 2.6-.2-1.6-.9-2.4-2.5-2.6 1.6-.2 2.3-1 2.5-2.6Z"
          fill="#30c7d2"
          stroke="#30c7d2"
        />
        <circle cx="25.5" cy="4.7" r="1.15" stroke="#5eead4" />
        <path d="M22.8 8.5c.5-1.35 1.4-2 2.7-2s2.2.65 2.7 2" stroke="#5eead4" />
      </g>
      <path
        data-mark="lake-contours"
        d="M5 10c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0M5 16c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0"
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M5 22c3.2-2.4 6.8-2.4 10.6 0s7.2 2.4 11.4 0"
        fill="none"
        stroke="#5eead4"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
