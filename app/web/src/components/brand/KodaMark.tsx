import { cn } from "@/lib/utils";
import { BRAND } from "@/lib/brand";
import { KodaOtterGraphic } from "./kodaMarkPaths";

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

/** Koda river-otter mascot — loyal trust ally; K on chest + proof badge. */
export function KodaMark({
  size = "md",
  className,
  gradientId = "koda-mark-gradient",
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
      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      <KodaOtterGraphic />
    </svg>
  );
}
