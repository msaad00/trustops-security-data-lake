import type { UseQueryOptions } from "@tanstack/react-query";

export const STALE = 15_000;
// Poll interval for "continuous" surfaces so posture/violations/connectors
// refresh on their own. Callers can override via `opts.refetchInterval`.
export const LIVE = 15_000;

export type Opts<T> = Omit<UseQueryOptions<T>, "queryKey" | "queryFn">;
