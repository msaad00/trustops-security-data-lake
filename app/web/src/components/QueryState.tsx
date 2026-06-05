import * as React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Minimal shape of a TanStack query result this component depends on. Accepting
 * a structural type keeps it usable with any `useQuery` hook without importing
 * the full generic.
 */
export interface QueryLike {
  isError: boolean;
  isPending: boolean;
  refetch: () => unknown;
}

function ErrorState({
  label,
  onRetry,
}: {
  label: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="m-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
    >
      <span className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 flex-none" />
        Couldn&rsquo;t load {label}. The API is unavailable or returned an error.
      </span>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 rounded-md border border-rose-300 bg-white px-2.5 py-1 font-semibold text-rose-700 outline-none hover:bg-rose-100 focus-visible:ring-2 focus-visible:ring-rose-400"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </button>
    </div>
  );
}

function DefaultSkeleton() {
  return (
    <div className="grid gap-2 p-5" aria-hidden>
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

/**
 * Gate content on one or more queries. Renders a retryable error banner when
 * any query failed and a skeleton while any is still loading, so a failed fetch
 * never renders as zero-filled "everything is fine" UI. Queries with `retry`
 * disabled (the console default) surface the failure immediately.
 */
export function QueryState({
  queries,
  label = "data",
  skeleton,
  children,
}: {
  queries: QueryLike | QueryLike[];
  label?: string;
  skeleton?: React.ReactNode;
  children: React.ReactNode;
}) {
  const list = Array.isArray(queries) ? queries : [queries];
  if (list.some((q) => q.isError)) {
    return (
      <ErrorState
        label={label}
        onRetry={() => list.forEach((q) => q.refetch())}
      />
    );
  }
  if (list.some((q) => q.isPending)) {
    return <>{skeleton ?? <DefaultSkeleton />}</>;
  }
  return <>{children}</>;
}
