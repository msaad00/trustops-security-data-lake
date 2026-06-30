"use client";

import {
  Bot,
  Brain,
  Cloud,
  CreditCard,
  HeartPulse,
  Landmark,
  Layers,
  Lock,
  Scale,
  Shield,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { FrameworkIconKey } from "@/lib/framework-visuals";
import { frameworkVisual } from "@/lib/framework-visuals";
import { cn } from "@/lib/utils";

const ICONS: Record<FrameworkIconKey, LucideIcon> = {
  shield: Shield,
  brain: Brain,
  lock: Lock,
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
  showIcon = true,
}: {
  frameworkId: string;
  fallbackLabel?: string;
  size?: number;
  className?: string;
  showIcon?: boolean;
}) {
  const visual = frameworkVisual(frameworkId, fallbackLabel);
  const Icon = ICONS[visual.icon] ?? Layers;

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-xl shadow-sm ring-1",
        className,
      )}
      style={{
        width: size,
        height: size,
        background: visual.gradient,
        boxShadow: `0 8px 20px ${visual.accent}33`,
        // ring color via inline style for dynamic palette
        outline: `1px solid ${visual.ring}`,
      }}
      role="img"
      aria-hidden
    >
      {showIcon ? (
        <Icon
          className="text-white drop-shadow-sm"
          size={Math.round(size * 0.46)}
          strokeWidth={2.25}
        />
      ) : (
        <span
          className="text-[10px] font-black tracking-wide text-white"
          style={{ fontSize: Math.max(9, size * 0.22) }}
        >
          {visual.mark}
        </span>
      )}
    </span>
  );
}
