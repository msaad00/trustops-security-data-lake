"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "../client";
import { LIVE, STALE, type Opts } from "./shared";
import type { Risk } from "../types";

export function useRisks(query = "", opts?: Opts<Risk[]>) {
  return useQuery({
    queryKey: ["risks", query],
    queryFn: () => api.risks(query),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useCreateRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<Risk> & { title: string }) =>
      api.createRisk(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

export function useUpdateRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Record<string, unknown>;
    }) => api.updateRisk(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}

export function useDeleteRiskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteRisk(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risks"] }),
  });
}
