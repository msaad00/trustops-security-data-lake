"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";

/**
 * Surfaces a clear warning when one or more API queries have failed.
 *
 * Without this, list pages fall back to `?? []` on a failed fetch and render
 * their cheerful empty state ("No violations", "0 open"), so a down backend
 * looks like a clean compliance posture. This subscribes to the query cache and
 * tells the user the data is incomplete — not an all-clear.
 */
export function ApiHealthBanner() {
  const cache = useQueryClient().getQueryCache();
  const errorCount = useSyncExternalStore(
    (onChange) => cache.subscribe(onChange),
    () =>
      cache.getAll().filter(
        (q) =>
          q.state.status === "error" &&
          // 501 means the feature is off on this install, not an outage.
          !/\b501\b/.test(String(q.state.error?.message ?? "")),
      ).length,
    () => 0,
  );

  if (errorCount === 0) return null;

  return (
    <div
      role="alert"
      className="mx-3 mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300 sm:mx-4"
    >
      Can&apos;t reach the assessment API — some data failed to load. What you
      see may be incomplete, not an all-clear. Check that the server is
      reachable and use Refresh to retry.
    </div>
  );
}
