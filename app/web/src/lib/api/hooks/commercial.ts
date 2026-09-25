import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { BillingStatus, ScimToken } from "@/lib/api/types";
import { STALE, type Opts } from "./shared";

export function useScimTokens(opts?: Opts<ScimToken[]>) {
  return useQuery({
    queryKey: ["scim-tokens"],
    queryFn: api.scimTokens,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useCreateScimTokenMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.createScimToken(name),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["scim-tokens"] });
    },
  });
}

export function useRevokeScimTokenMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (tokenId: string) => api.revokeScimToken(tokenId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["scim-tokens"] });
    },
  });
}

export function useBilling(opts?: Opts<BillingStatus>) {
  return useQuery({
    queryKey: ["billing"],
    queryFn: api.billing,
    staleTime: STALE,
    retry: false,
    ...opts,
  });
}

export function useBillingCheckoutMutation() {
  return useMutation({
    mutationFn: (plan: string) => api.billingCheckout(plan),
  });
}

export function useBillingPortalMutation() {
  return useMutation({ mutationFn: () => api.billingPortal() });
}
