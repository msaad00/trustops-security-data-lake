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

/** Koda mark — bold K lettermark with otter ears + proof badge. */
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
      {/* Otter ears — mascot hint above the K */}
      <ellipse cx="11" cy="8.2" rx="2.4" ry="2.1" fill="#fff" opacity="0.95" />
      <ellipse cx="19.5" cy="7.8" rx="2.4" ry="2.1" fill="#fff" opacity="0.95" />
      <ellipse cx="11" cy="8.2" rx="1.1" ry="0.9" fill="#dbeafe" />
      <ellipse cx="19.5" cy="7.8" rx="1.1" ry="0.9" fill="#dbeafe" />
      {/* K lettermark */}
      <path
        d="M8.5 9h4.2v5.1L19.8 9h4.9l-7.8 7.2 8.1 9.8h-5.1l-6.2-7.6V26H8.5z"
        fill="#fff"
      />
      {/* Otter snout dot — friendly mascot nose at K junction */}
      <ellipse cx="13.2" cy="15.8" rx="1.1" ry="0.85" fill="#e2e8f0" />
      <ellipse cx="13.2" cy="15.6" rx="0.55" ry="0.4" fill="#101623" />
      {/* Proof badge */}
      <circle cx="24.5" cy="24.5" r="6.2" fill="#fff" />
      <path
        d="M21.5 24.5l1.8 1.8 3.8-3.8"
        stroke="#047857"
        strokeWidth="1.7"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
