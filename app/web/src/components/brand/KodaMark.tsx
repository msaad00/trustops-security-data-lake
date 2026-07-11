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

/** Koda otter mascot with K on chest + proof badge. */
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
      {/* Otter head */}
      <ellipse cx="16" cy="16.2" rx="10.2" ry="9.5" fill="#fff" />
      {/* Ears */}
      <circle cx="9.4" cy="9.8" r="2.5" fill="#fff" />
      <circle cx="22.6" cy="9.8" r="2.5" fill="#fff" />
      <circle cx="9.4" cy="9.8" r="1.15" fill="#dbeafe" />
      <circle cx="22.6" cy="9.8" r="1.15" fill="#dbeafe" />
      {/* Eyes */}
      <circle cx="12.5" cy="15.1" r="1.55" fill="#101623" />
      <circle cx="19.5" cy="15.1" r="1.55" fill="#101623" />
      <circle cx="13" cy="14.55" r="0.45" fill="#fff" />
      <circle cx="20" cy="14.55" r="0.45" fill="#fff" />
      {/* Snout */}
      <ellipse cx="16" cy="19.6" rx="3.2" ry="2.2" fill="#f1f5f9" />
      <ellipse cx="16" cy="19.2" rx="1.45" ry="0.95" fill="#101623" />
      {/* Whiskers */}
      <path
        d="M11.2 18.4h-2.1M20.8 18.4h2.1M10.8 19.8h-2.3M21.2 19.8h2.3"
        stroke="#94a3b8"
        strokeWidth="0.55"
        strokeLinecap="round"
      />
      {/* Belly patch + K monogram */}
      <ellipse cx="16" cy="22" rx="4.6" ry="3.4" fill="#eef4ff" />
      <path
        d="M13.2 20.1h2v2.2l2.7-2.2h2.2l-2.9 2.6 3 3.6h-2.2l-2.5-3v3h-2z"
        fill="#3b6ef5"
      />
      {/* Proof badge */}
      <circle cx="24.4" cy="24.4" r="5.6" fill="#fff" />
      <path
        d="M21.9 24.4l1.55 1.55 3.35-3.35"
        stroke="#047857"
        strokeWidth="1.65"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
