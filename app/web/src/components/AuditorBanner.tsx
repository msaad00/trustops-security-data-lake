"use client";

import { ShieldCheck } from "lucide-react";
import { useAuditorMode } from "@/lib/state/auditor";

export function AuditorBanner() {
  const auditor = useAuditorMode();
  if (!auditor) return null;
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 sm:px-5 lg:px-7">
      <span className="inline-flex items-center gap-2 font-extrabold">
        <ShieldCheck className="h-4 w-4" />
        Auditor view — read-only. Owners, assignees, and remediation notes are
        redacted.
      </span>
      <a
        href="?"
        className="rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs font-black text-amber-800 hover:bg-amber-100"
      >
        Exit auditor mode
      </a>
    </div>
  );
}
