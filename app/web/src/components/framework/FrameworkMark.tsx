"use client";

import Image from "next/image";
import {
  Bot,
  BrainCircuit,
  Cloud,
  CreditCard,
  HeartPulse,
  Landmark,
  Layers,
  LockKeyhole,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { frameworkVisual } from "@/lib/framework-visuals";
import { cn } from "@/lib/utils";

const ICONS = {
  shield: ShieldCheck,
  brain: BrainCircuit,
  lock: LockKeyhole,
  sparkles: Sparkles,
  "heart-pulse": HeartPulse,
  "credit-card": CreditCard,
  scale: Scale,
  bot: Bot,
  cloud: Cloud,
  landmark: Landmark,
  layers: Layers,
};

export function FrameworkMark({
  frameworkId,
  fallbackLabel,
  size = 40,
  className,
}: {
  frameworkId: string;
  fallbackLabel?: string;
  size?: number;
  className?: string;
}) {
  const visual = frameworkVisual(frameworkId, fallbackLabel);
  const Icon = ICONS[visual.icon];

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg border font-black",
        className,
      )}
      style={{
        width: size,
        height: size,
        background: visual.bg,
        borderColor: visual.ring,
        color: visual.accent,
      }}
      role="img"
      aria-label={`${visual.label} framework`}
    >
      {visual.artwork ? (
        <Image
          src={visual.artwork}
          alt=""
          width={size}
          height={size}
          className="h-full w-full object-contain p-0.5"
          title={`${visual.attribution}; NIST does not endorse TrustOps`}
        />
      ) : (
        <span className="grid place-items-center gap-0.5" aria-hidden="true">
          <Icon style={{ width: size * 0.36, height: size * 0.36 }} />
          <span
            className="tracking-tight"
            style={{ fontSize: Math.max(8, size * 0.18) }}
          >
            {visual.mark}
          </span>
        </span>
      )}
    </span>
  );
}
