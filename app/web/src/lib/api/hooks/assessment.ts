"use client";

import { useEffect, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api, bootstrapAssessment } from "../client";
import { LIVE, STALE, type Opts } from "./shared";
import type {
  AssetRisk,
  ControlPosture,
  ControlTest,
  EscalateFreshnessResult,
  EvidenceFreshness,
  EvidenceFreshnessSummary,
  NormalizedEvent,
  SnapshotSummary,
  TrackingEvent,
  TriagePayload,
  VerifyResult,
  Violation,
} from "../types";

export function useControls(opts?: Opts<ControlPosture[]>) {
  return useQuery({
    queryKey: ["controls"],
    queryFn: async () => (await api.controls()).controls ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useControlTests(opts?: Opts<ControlTest[]>) {
  return useQuery({
    queryKey: ["control-tests"],
    queryFn: async () => (await api.controlTests()).control_tests ?? [],
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useViolations(opts?: Opts<Violation[]>) {
  return useQuery({
    queryKey: ["violations"],
    queryFn: async () => (await api.violations()).violations ?? [],
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useEvidence(opts?: Opts<NormalizedEvent[]>) {
  return useQuery({
    queryKey: ["evidence"],
    queryFn: async () => (await api.evidence()).evidence ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useEvidenceFreshness(opts?: Opts<EvidenceFreshness[]>) {
  return useQuery({
    queryKey: ["evidence", "freshness"],
    queryFn: () => api.evidenceFreshness(),
    staleTime: STALE,
    refetchInterval: LIVE,
    refetchOnWindowFocus: true,
    ...opts,
  });
}

export function useEvidenceFreshnessSummary(
  opts?: Opts<EvidenceFreshnessSummary>,
) {
  return useQuery({
    queryKey: ["evidence", "freshness", "summary"],
    queryFn: api.authFreshnessSummary,
    staleTime: STALE,
    refetchInterval: LIVE,
    ...opts,
  });
}

export function useEscalateStaleEvidenceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (limit: number) => api.escalateStaleEvidence(limit),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["evidence", "freshness"] });
      void qc.invalidateQueries({ queryKey: ["remediation", "tasks"] });
      void qc.invalidateQueries({ queryKey: ["platform", "audit-readiness"] });
    },
  });
}

export function useAssets(opts?: Opts<AssetRisk[]>) {
  return useQuery({
    queryKey: ["assets"],
    queryFn: async () => (await api.assets()).assets ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useSnapshots(opts?: Opts<SnapshotSummary[]>) {
  return useQuery({
    queryKey: ["snapshots"],
    queryFn: async () => (await api.listSnapshots()).snapshots ?? [],
    staleTime: STALE,
    ...opts,
  });
}

export function useSnapshotDetail(snapshotId: string | undefined) {
  return useQuery({
    queryKey: ["snapshots", "detail", snapshotId],
    queryFn: () => api.getSnapshotDetail(snapshotId!),
    enabled: Boolean(snapshotId),
    staleTime: STALE,
  });
}

export function useTracking(violationId: string | null) {
  return useQuery({
    queryKey: ["tracking", violationId],
    queryFn: async () => {
      if (!violationId)
        return { events: [] as TrackingEvent[], current_state: "open" };
      const data = await api.getTracking(violationId);
      return { events: data.events, current_state: data.current_state };
    },
    enabled: Boolean(violationId),
    staleTime: 5_000,
  });
}

export function useTriageMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      violationId,
      payload,
    }: {
      violationId: string;
      payload: TriagePayload;
    }) => api.triage(violationId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["tracking", vars.violationId] });
    },
  });
}

export function useVerifyMutation() {
  return useMutation({
    mutationFn: (eventId: string) => api.verifyEvidence(eventId),
  });
}

export function useSnapshotMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => api.createSnapshot(reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["snapshots"] });
    },
  });
}
