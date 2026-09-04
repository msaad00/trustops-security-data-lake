import Link from "next/link";
import { cn } from "@/lib/utils";
import { BRAND } from "@/lib/brand";
import { TrustOpsMark } from "./TrustOpsMark";

interface Props {
  /** Show wordmark text beside the monogram. */
  showWordmark?: boolean;
  /** Optional subtitle under the wordmark (e.g. "Console"). */
  subtitle?: string;
  /** Link target; omit for static branding (no link). */
  href?: string;
  markSize?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
  /** Light text for dark headers (TopBar). */
  inverted?: boolean;
  gradientId?: string;
  wordmarkClassName?: string;
}

export function TrustOpsLogo({
  showWordmark = true,
  subtitle,
  href,
  markSize = "md",
  className,
  inverted = false,
  gradientId,
  wordmarkClassName,
}: Props) {
  const content = (
    <>
      <TrustOpsMark size={markSize} gradientId={gradientId} />
      {showWordmark && (
        <span className={cn("min-w-0 leading-tight", wordmarkClassName)}>
          <span
            className={cn(
              "block truncate font-black tracking-tight",
              inverted ? "text-white" : "text-ink",
              markSize === "sm" || markSize === "xs" ? "text-sm" : "text-lg",
            )}
          >
            <span className="mr-[0.22em] inline-block">
              {BRAND.wordmarkPrimary}
            </span>
            <span className={inverted ? "text-cyan-300" : "text-[#0f8f91]"}>
              {BRAND.wordmarkAccent}
            </span>
          </span>
          {subtitle && (
            <span
              className={cn(
                "block truncate text-[10px] font-black uppercase tracking-[0.16em]",
                inverted ? "text-[#9aa9bc]" : "text-muted",
              )}
            >
              {subtitle}
            </span>
          )}
        </span>
      )}
    </>
  );

  const classes = cn("inline-flex min-w-0 items-center gap-2", className);

  if (href) {
    return (
      <Link href={href} className={cn(classes, "hover:opacity-90")}>
        {content}
      </Link>
    );
  }

  return <div className={classes}>{content}</div>;
}
