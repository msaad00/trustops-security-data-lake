"use client";

import { useEffect } from "react";
import { Camera, RefreshCw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TrustOpsLogo } from "@/components/brand/TrustOpsLogo";
import { NotificationBell } from "./NotificationBell";
import { UserMenu } from "./UserMenu";
import { useHealth } from "@/lib/api/hooks";

interface Props {
  onRefresh: () => void;
  onSnapshot: () => void;
  onOpenPalette: () => void;
}

export function TopBar({ onRefresh, onSnapshot, onOpenPalette }: Props) {
  const { data } = useHealth();
  const live = data?.ok ?? null;

  // cmd/ctrl + K opens the palette anywhere in the app.
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const isPalette =
        (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      if (isPalette) {
        event.preventDefault();
        onOpenPalette();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onOpenPalette]);

  return (
    <header className="sticky top-0 z-40 flex h-[52px] min-w-0 items-center justify-between gap-1.5 overflow-hidden border-b border-white/10 bg-rail/95 px-2 text-slate-100 shadow-[0_8px_30px_rgba(2,6,23,0.18)] backdrop-blur-xl md:px-3">
      <TrustOpsLogo
        href="/dashboard"
        inverted
        markSize="lg"
        showWordmark
        wordmarkClassName="hidden xl:block"
        className="flex-none"
        gradientId="trustops-topbar-gradient"
      />
      <button
        type="button"
        onClick={onOpenPalette}
        aria-label="Open command palette"
        className="group flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-[#27364a] bg-[#101926] text-left text-sm text-[#7d8ca3] hover:border-[#3b4d68] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-rail md:min-w-[150px] md:flex-1 md:justify-start md:gap-2.5 md:pl-3 md:pr-2 xl:max-w-[440px] 2xl:max-w-[520px]"
      >
        <Search className="h-4 w-4 text-[#5b6a7e]" />
        <span className="hidden flex-1 truncate md:block">
          Search controls, evidence, owners, assets, workflows…
        </span>
        <kbd className="hidden rounded border border-[#27364a] bg-[#0b1118] px-1.5 py-0.5 text-[10px] font-bold text-[#9aa9bc] xl:block">
          ⌘K
        </kbd>
      </button>
      <div className="flex min-w-0 flex-none items-center gap-1.5">
        <div className="hidden md:block">
          <UserMenu />
        </div>
        <span
          className={[
            "hidden h-9 items-center gap-2 rounded-lg border px-2.5 text-sm font-extrabold 2xl:inline-flex",
            live
              ? "border-emerald-300 bg-emerald-50 text-emerald-700"
              : "border-amber-300 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          <span
            className={[
              "h-2.5 w-2.5 rounded-full",
              live ? "bg-emerald-500" : "bg-amber-500",
            ].join(" ")}
          />
          {live === null ? "API checking" : live ? "API live" : "static mode"}
        </span>
        <div className="hidden lg:block">
          <NotificationBell />
        </div>
        <Button
          variant="default"
          size="sm"
          onClick={onRefresh}
          aria-label="Refresh data"
        >
          <RefreshCw className="h-4 w-4" />
          <span className="hidden 2xl:inline">Refresh</span>
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={onSnapshot}
          aria-label="Capture snapshot"
        >
          <Camera className="h-4 w-4" />
          <span className="hidden 2xl:inline">Snapshot</span>
        </Button>
      </div>
    </header>
  );
}
