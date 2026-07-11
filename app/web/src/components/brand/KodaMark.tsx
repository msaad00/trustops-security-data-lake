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
      aria-label="Koda"
      className={cn("flex-none", SIZES[size], className)}
    >
      <title>Koda</title>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4f7cff" />
          <stop offset="100%" stopColor="#30c7d2" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      {/* Otter head */}
      <ellipse cx="16" cy="16.5" rx="10.5" ry="9.8" fill="#fff" />
      {/* Ears */}
      <circle cx="9.2" cy="9.5" r="2.6" fill="#fff" />
      <circle cx="22.8" cy="9.5" r="2.6" fill="#fff" />
      <circle cx="9.2" cy="9.5" r="1.2" fill="#dbeafe" />
      <circle cx="22.8" cy="9.5" r="1.2" fill="#dbeafe" />
      {/* Eyes */}
      <circle cx="12.4" cy="15.2" r="1.45" fill="#101623" />
      <circle cx="19.6" cy="15.2" r="1.45" fill="#101623" />
      <circle cx="12.85" cy="14.75" r="0.4" fill="#fff" />
      <circle cx="20.05" cy="14.75" r="0.4" fill="#fff" />
      {/* Snout */}
      <ellipse cx="16" cy="19.8" rx="3.4" ry="2.4" fill="#f1f5f9" />
      <ellipse cx="16" cy="19.4" rx="1.5" ry="1" fill="#101623" />
      {/* Belly patch + K monogram on otter */}
      <ellipse cx="16" cy="22.2" rx="4.8" ry="3.6" fill="#eef4ff" />
      <path
        d="M13.4 20.2h1.8v2.1l2.6-2.1h2.1l-2.8 2.5 2.9 3.5h-2.1l-2.4-2.9v2.9h-1.8z"
        fill="#4f7cff"
      />
      {/* Proof badge */}
      <circle cx="24.5" cy="24.5" r="5.8" fill="#fff" />
      <path
        d="M22 24.5l1.6 1.6 3.4-3.4"
        stroke="#047857"
        strokeWidth="1.6"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
