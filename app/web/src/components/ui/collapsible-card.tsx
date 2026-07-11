"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card } from "./card";
import { usePersistentState } from "@/lib/state/preferences";
import { cn } from "@/lib/utils";

interface Props {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /**
   * Stable identifier used to persist open/closed state across reloads.
   * Pages should pass a deterministic key per section.
   */
  storageKey?: string;
  defaultOpen?: boolean;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function CollapsibleCard({
  title,
  description,
  actions,
  storageKey,
  defaultOpen = true,
  children,
  className,
  contentClassName,
}: Props) {
  // Two-mode state so non-storage callers don't pay the localStorage cost.
  const [localOpen, setLocalOpen] = useState(defaultOpen);
  const [persistedOpen, setPersistedOpen] = usePersistentState(
    storageKey ? `trustops:section:${storageKey}` : "trustops:section:_unused",
    defaultOpen,
  );
  const open = storageKey ? persistedOpen : localOpen;
  const setOpen = storageKey ? setPersistedOpen : setLocalOpen;

  return (
    <Card className={cn("overflow-hidden", className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start justify-between gap-3 p-5 text-left"
      >
        <span className="grid min-w-0 gap-1">
          <span className="flex items-center gap-2 text-lg font-black leading-tight">
            {open ? (
              <ChevronDown className="h-4 w-4 text-muted" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted" />
            )}
            {title}
          </span>
          {description && (
            <span className="block text-sm text-muted">{description}</span>
          )}
        </span>
        {actions && (
          <span
            className="flex items-center gap-2"
            onClick={(event) => event.stopPropagation()}
          >
            {actions}
          </span>
        )}
      </button>
      {open && (
        <div className={cn("border-t border-line p-5", contentClassName)}>
          {children}
        </div>
      )}
    </Card>
  );
}
