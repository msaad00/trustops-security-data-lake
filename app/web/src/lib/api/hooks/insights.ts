"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import { LIVE, STALE } from "./shared";

export function useInsightsTimeseries(limit = 90) {
  return useQuery({
    queryKey: ["insights", "timeseries", limit],
    queryFn: () => api.insightsTimeseries(limit),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useInsightsRemediation() {
  return useQuery({
    queryKey: ["insights", "remediation"],
    queryFn: api.insightsRemediation,
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useCaptureMetricMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.insightsCapture,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["insights", "timeseries"] }),
  });
}

export function useInsightsFrameworkTrends(limit = 90) {
  return useQuery({
    queryKey: ["insights", "framework-trends", limit],
    queryFn: () => api.insightsFrameworkTrends(limit),
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}

export function useInsightsSlaHeatmap() {
  return useQuery({
    queryKey: ["insights", "sla-heatmap"],
    queryFn: api.insightsSlaHeatmap,
    staleTime: STALE,
    refetchInterval: LIVE,
  });
}
